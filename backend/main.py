from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
import yfinance as yf
from datetime import datetime, timedelta
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import pandas as pd
from dotenv import load_dotenv
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)



load_dotenv()
API_KEY = os.getenv("NEWS_API_KEY")

TICKER_MAP = {
    "Reliance Industries": "RELIANCE.NS",
    "TCS": "TCS.NS",
    "Infosys": "INFY.NS",
    "HDFC Bank": "HDFCBANK.NS",
    "Wipro": "WIPRO.NS"
}

analyzer = SentimentIntensityAnalyzer()

def get_label(score):
    if score >= 0.05:
        return "Bullish"
    elif score <= -0.05:
        return "Bearish"
    else:
        return "Neutral"

def fetch_stock_price(ticker):
    try:
        stock_data = yf.download(ticker, period="1mo", interval="1d", progress=False)
        if stock_data.empty:
            t = yf.Ticker(ticker)
            stock_data = t.history(period="1mo")
        if stock_data.empty:
            return None
        stock_data.index = pd.to_datetime(stock_data.index)
        if stock_data.index.tz is not None:
            stock_data.index = stock_data.index.tz_localize(None)
        stock_data = stock_data[["Close"]].reset_index()
        stock_data.columns = ["date", "close_price"]
        stock_data["date"] = stock_data["date"].dt.strftime('%Y-%m-%d')
        return stock_data
    except:
        return None

@app.get("/lookup/{symbol}")
def lookup(symbol: str):
    try:
        info = yf.Ticker(f"{symbol}.NS").info
        name = info.get("longName") or info.get("shortName") or symbol
        return {"symbol": symbol, "name": name}
    except:
        return {"symbol": symbol, "name": symbol}

@app.get("/analyze/{stock_name}")
def analyze(stock_name: str, company_name: str = None):
    search_term = company_name or stock_name
    end_date = datetime.today().strftime('%Y-%m-%d')
    start_date = (datetime.today() - timedelta(days=30)).strftime('%Y-%m-%d')
    url = (
        f"https://newsapi.org/v2/everything?"
        f"q={search_term} stock India&"
        f"from={start_date}&to={end_date}&"
        f"language=en&sortBy=publishedAt&apiKey={API_KEY}"
    )
    data = requests.get(url).json()
    if data["status"] != "ok":
        return {"error": data["message"]}

    articles = []
    for a in data["articles"]:
        score = analyzer.polarity_scores(a["title"])["compound"]
        articles.append({
            "date": a["publishedAt"][:10],
            "headline": a["title"],
            "source": a["source"]["name"],
            "sentiment_score": score,
            "sentiment_label": get_label(score)
        })

    if not articles:
        return {"error": f"No news found for {search_term}"}

    df = pd.DataFrame(articles).drop_duplicates(subset="headline")
    daily = df.groupby("date")["sentiment_score"].mean().reset_index()
    daily.columns = ["date", "avg_sentiment"]

    ticker = TICKER_MAP.get(stock_name, f"{stock_name}.NS")
    stock_data = fetch_stock_price(ticker)
    has_price = stock_data is not None and not stock_data.empty

    if has_price:
        merged = pd.merge(daily, stock_data, on="date", how="inner")
        corr = merged["avg_sentiment"].corr(merged["close_price"]) if len(merged) > 1 else 0
        chart_data = [
            {
                "date": str(row["date"]),
                "avg_sentiment": round(float(row["avg_sentiment"]), 3),
                "close_price": round(float(row["close_price"]), 2)
            }
            for _, row in merged.iterrows()
        ]
    else:
        corr = 0
        chart_data = [
            {
                "date": str(row["date"]),
                "avg_sentiment": round(float(row["avg_sentiment"]), 3),
                "close_price": None
            }
            for _, row in daily.iterrows()
        ]

    source_counts = df["source"].value_counts().head(5).to_dict()
    bullish_count = len(df[df["sentiment_label"] == "Bullish"])
    bearish_count = len(df[df["sentiment_label"] == "Bearish"])
    neutral_count = len(df[df["sentiment_label"] == "Neutral"])

    return {
        "stock": stock_name,
        "company_name": search_term,
        "total_headlines": len(df),
        "latest_score": round(float(daily["avg_sentiment"].iloc[-1]), 3) if len(daily) else 0,
        "latest_label": get_label(float(daily["avg_sentiment"].iloc[-1])) if len(daily) else "Neutral",
        "correlation": round(float(corr), 3) if not pd.isna(corr) else 0,
        "has_price": has_price,
        "chart_data": chart_data,
        "source_counts": source_counts,
        "sentiment_distribution": {
            "Bullish": bullish_count,
            "Bearish": bearish_count,
            "Neutral": neutral_count
        },
        "headlines": [
            {
                "date": str(row["date"]),
                "headline": str(row["headline"]),
                "source": str(row["source"]),
                "sentiment_score": round(float(row["sentiment_score"]), 3),
                "sentiment_label": str(row["sentiment_label"])
            }
            for _, row in df.head(20).iterrows()
        ]
    }

@app.get("/pulse")
def pulse():
    results = []
    for stock in TICKER_MAP:
        end_date = datetime.today().strftime('%Y-%m-%d')
        start_date = (datetime.today() - timedelta(days=7)).strftime('%Y-%m-%d')
        url = (
            f"https://newsapi.org/v2/everything?"
            f"q={stock} stock India&"
            f"from={start_date}&to={end_date}&"
            f"language=en&sortBy=publishedAt&pageSize=10&apiKey={API_KEY}"
        )
        data = requests.get(url).json()
        if data["status"] != "ok":
            continue
        scores = [analyzer.polarity_scores(a["title"])["compound"] for a in data["articles"]]
        avg = sum(scores) / len(scores) if scores else 0
        results.append({
            "stock": stock,
            "score": round(avg, 3),
            "label": get_label(avg)
        })
    return results

@app.get("/heatmap")
def heatmap():
    results = []
    for stock in TICKER_MAP:
        end_date = datetime.today().strftime('%Y-%m-%d')
        start_date = (datetime.today() - timedelta(days=7)).strftime('%Y-%m-%d')
        url = (
            f"https://newsapi.org/v2/everything?"
            f"q={stock} stock India&"
            f"from={start_date}&to={end_date}&"
            f"language=en&sortBy=publishedAt&pageSize=20&apiKey={API_KEY}"
        )
        data = requests.get(url).json()
        if data["status"] != "ok":
            continue
        scores = [analyzer.polarity_scores(a["title"])["compound"] for a in data["articles"]]
        if not scores:
            continue
        avg = sum(scores) / len(scores)
        results.append({
            "stock": stock,
            "score": round(avg, 3),
            "label": get_label(avg),
            "bullish": len([s for s in scores if s >= 0.05]),
            "bearish": len([s for s in scores if s <= -0.05]),
            "neutral": len([s for s in scores if -0.05 < s < 0.05]),
            "total": len(scores)
        })
    return results

@app.get("/wordcloud/{stock_name}")
def wordcloud_data(stock_name: str, company_name: str = None):
    search_term = company_name or stock_name
    end_date = datetime.today().strftime('%Y-%m-%d')
    start_date = (datetime.today() - timedelta(days=30)).strftime('%Y-%m-%d')
    url = (
        f"https://newsapi.org/v2/everything?"
        f"q={search_term} stock India&"
        f"from={start_date}&to={end_date}&"
        f"language=en&sortBy=publishedAt&apiKey={API_KEY}"
    )
    data = requests.get(url).json()
    if data["status"] != "ok":
        return {"bullish_words": {}, "bearish_words": {}}

    stop_words = {
        "the","a","an","in","on","at","to","for","of","and","or","but",
        "is","are","was","were","be","been","being","have","has","had",
        "do","does","did","will","would","could","should","may","might",
        "this","that","these","those","it","its","with","from","by","as",
        "stock","india","share","market","nse","bse","sensex","nifty",
        "says","said","after","before","over","under","more","less","new",
        "company","ltd","limited","inc","corp","group","report","quarter"
    }

    bullish_words = {}
    bearish_words = {}

    for a in data["articles"]:
        score = analyzer.polarity_scores(a["title"])["compound"]
        words = a["title"].lower().split()
        words = [w.strip(".,!?\"'()[]{}") for w in words if len(w) > 3 and w not in stop_words]
        target = bullish_words if score >= 0.05 else bearish_words if score <= -0.05 else None
        if target is not None:
            for w in words:
                target[w] = target.get(w, 0) + 1

    top_bullish = dict(sorted(bullish_words.items(), key=lambda x: x[1], reverse=True)[:40])
    top_bearish = dict(sorted(bearish_words.items(), key=lambda x: x[1], reverse=True)[:40])

    return {"bullish_words": top_bullish, "bearish_words": top_bearish}
