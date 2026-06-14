import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import requests
import yfinance as yf
from datetime import datetime, timedelta
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# Config
st.set_page_config(page_title="Indian Stock Sentiment Analyzer", layout="wide")

API_KEY = "248e488fe67c41b3a889d72a1355bb6a"

TICKER_MAP = {
    "Reliance Industries": "RELIANCE.NS",
    "TCS": "TCS.NS",
    "Infosys": "INFY.NS",
    "HDFC Bank": "HDFCBANK.NS",
    "Wipro": "WIPRO.NS"
}

analyzer = SentimentIntensityAnalyzer()

def fetch_news(stock_name, days=30):
    end_date = datetime.today().strftime('%Y-%m-%d')
    start_date = (datetime.today() - timedelta(days=days)).strftime('%Y-%m-%d')
    url = (
        f"https://newsapi.org/v2/everything?"
        f"q={stock_name} stock India&"
        f"from={start_date}&to={end_date}&"
        f"language=en&sortBy=publishedAt&apiKey={API_KEY}"
    )
    response = requests.get(url)
    data = response.json()
    if data["status"] != "ok":
        return None
    articles = []
    for article in data["articles"]:
        articles.append({
            "date": article["publishedAt"][:10],
            "headline": article["title"],
            "source": article["source"]["name"]
        })
    df = pd.DataFrame(articles).drop_duplicates(subset="headline")
    return df

def get_sentiment(headline):
    score = analyzer.polarity_scores(headline)["compound"]
    return score

def get_label(score):
    if score >= 0.05: return "🟢 Bullish"
    elif score <= -0.05: return "🔴 Bearish"
    else: return "⚪ Neutral"

def get_stock_price(ticker):
    data = yf.download(ticker, period="1mo", interval="1d", progress=False)
    data = data[["Close"]].reset_index()
    data.columns = ["date", "close_price"]
    data["date"] = data["date"].astype(str).str[:10]
    return data

def plot_chart(merged, stock_name):
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    colors = ["green" if s >= 0.05 else "red" if s <= -0.05 else "gray"
              for s in merged["avg_sentiment"]]
    fig.add_trace(go.Bar(
        x=merged["date"], y=merged["avg_sentiment"],
        name="Sentiment Score", marker_color=colors, opacity=0.6
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=merged["date"], y=merged["close_price"],
        name="Stock Price (₹)", line=dict(color="royalblue", width=2),
        mode="lines+markers"
    ), secondary_y=True)
    fig.update_layout(
        title=f"{stock_name} — Sentiment vs Stock Price",
        xaxis_title="Date",
        legend=dict(x=0, y=1.1, orientation="h"),
        plot_bgcolor="white", hovermode="x unified"
    )
    fig.update_yaxes(title_text="Sentiment Score (-1 to +1)", secondary_y=False)
    fig.update_yaxes(title_text="Stock Price (₹)", secondary_y=True)
    return fig

# ── UI ──────────────────────────────────────────────────────────────

st.title("📈 Indian Stock Sentiment Analyzer")
st.caption("Real-time news sentiment vs stock price movement for Nifty 50 stocks")

col1, col2 = st.columns([1, 3])

with col1:
    stock = st.selectbox("Select Stock", list(TICKER_MAP.keys()))
    analyze = st.button("Analyze", use_container_width=True)

if analyze:
    with st.spinner(f"Fetching news for {stock}..."):
        news_df = fetch_news(stock, days=30)

    if news_df is None or news_df.empty:
        st.error("Could not fetch news. Check your API key.")
    else:
        # Run sentiment
        news_df["sentiment_score"] = news_df["headline"].apply(get_sentiment)
        news_df["sentiment_label"] = news_df["sentiment_score"].apply(get_label)

        # Daily average
        daily = news_df.groupby("date")["sentiment_score"].mean().reset_index()
        daily.columns = ["date", "avg_sentiment"]

        # Stock price
        with st.spinner("Fetching stock price..."):
            price_df = get_stock_price(TICKER_MAP[stock])

        merged = pd.merge(daily, price_df, on="date", how="inner")

        # Today's mood
        latest_score = daily["avg_sentiment"].iloc[-1]
        label = get_label(latest_score)

        st.markdown("---")
        m1, m2, m3 = st.columns(3)
        m1.metric("Today's Market Mood", label)
        m2.metric("Sentiment Score", f"{latest_score:.3f}")
        m3.metric("Headlines Analyzed", len(news_df))

        # Chart
        st.plotly_chart(plot_chart(merged, stock), use_container_width=True)

        # Correlation
        if len(merged) > 1:
            corr = merged["avg_sentiment"].corr(merged["close_price"])
            st.info(f"📊 Correlation between sentiment and price: **{corr:.2f}**")

        # Headlines table
        st.markdown("### 📰 Recent Headlines")
