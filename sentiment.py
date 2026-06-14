import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import yfinance as yf
import os

# Stock name to Yahoo Finance ticker mapping
TICKER_MAP = {
    "Reliance Industries": "RELIANCE.NS",
    "TCS": "TCS.NS",
    "Infosys": "INFY.NS",
    "HDFC Bank": "HDFCBANK.NS",
    "Wipro": "WIPRO.NS"
}

analyzer = SentimentIntensityAnalyzer()

def get_sentiment(headline):
    score = analyzer.polarity_scores(headline)
    return score["compound"]  # compound is the overall score (-1 to +1)

def get_label(score):
    if score >= 0.05:
        return "Bullish"
    elif score <= -0.05:
        return "Bearish"
    else:
        return "Neutral"

def analyze_stock(stock_name):
    # Load news CSV
    csv_path = f"data/{stock_name}_news.csv"
    if not os.path.exists(csv_path):
        print(f"No data found for {stock_name}")
        return None

    df = pd.read_csv(csv_path)

    # Run sentiment on every headline
    df["sentiment_score"] = df["headline"].apply(get_sentiment)
    df["sentiment_label"] = df["sentiment_score"].apply(get_label)

    # Average sentiment per day
    daily = df.groupby("date")["sentiment_score"].mean().reset_index()
    daily.columns = ["date", "avg_sentiment"]

    # Fetch stock price from Yahoo Finance
    ticker = TICKER_MAP.get(stock_name)
    if not ticker:
        print(f"No ticker found for {stock_name}")
        return None

    stock_data = yf.download(ticker, period="1mo", interval="1d", progress=False)
    stock_data = stock_data[["Close"]].reset_index()
    stock_data.columns = ["date", "close_price"]
    stock_data["date"] = stock_data["date"].astype(str).str[:10]

    # Merge sentiment + price on date
    merged = pd.merge(daily, stock_data, on="date", how="inner")
    merged["stock"] = stock_name

    # Save result
    merged.to_csv(f"data/{stock_name}_analyzed.csv", index=False)
    print(f"Analyzed {stock_name}: {len(merged)} days of data")
    print(merged.head())
    print()

    return merged

if __name__ == "__main__":
    stocks = ["Reliance Industries", "TCS", "Infosys", "HDFC Bank", "Wipro"]
    for stock in stocks:
        analyze_stock(stock)