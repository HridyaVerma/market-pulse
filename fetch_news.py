import requests
import pandas as pd
from datetime import datetime, timedelta

API_KEY = "248e488fe67c41b3a889d72a1355bb6a"

def fetch_news(stock_name, days=30):
    end_date = datetime.today().strftime('%Y-%m-%d')
    start_date = (datetime.today() - timedelta(days=days)).strftime('%Y-%m-%d')

    url = (
        f"https://newsapi.org/v2/everything?"
        f"q={stock_name} stock India&"
        f"from={start_date}&"
        f"to={end_date}&"
        f"language=en&"
        f"sortBy=publishedAt&"
        f"apiKey={API_KEY}"
    )

    response = requests.get(url)
    data = response.json()

    if data["status"] != "ok":
        print(f"Error: {data['message']}")
        return None

    articles = []
    for article in data["articles"]:
        articles.append({
            "date": article["publishedAt"][:10],
            "headline": article["title"],
            "source": article["source"]["name"]
        })

    df = pd.DataFrame(articles)
    df = df.drop_duplicates(subset="headline")
    df.to_csv(f"data/{stock_name}_news.csv", index=False)
    print(f"Saved {len(df)} headlines to data/{stock_name}_news.csv")

    return df

if __name__ == "__main__":
    stocks = ["Reliance Industries", "TCS", "Infosys", "HDFC Bank", "Wipro"]
    for stock in stocks:
        fetch_news(stock, days=30)