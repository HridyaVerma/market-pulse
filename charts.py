import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

def plot_stock(stock_name):
    csv_path = f"data/{stock_name}_analyzed.csv"
    if not os.path.exists(csv_path):
        print(f"No analyzed data for {stock_name}")
        return

    df = pd.read_csv(csv_path)

    # Create dual-axis chart
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Sentiment bar chart (primary y-axis)
    colors = ["green" if s >= 0.05 else "red" if s <= -0.05 else "gray"
              for s in df["avg_sentiment"]]

    fig.add_trace(
        go.Bar(
            x=df["date"],
            y=df["avg_sentiment"],
            name="Sentiment Score",
            marker_color=colors,
            opacity=0.6
        ),
        secondary_y=False
    )

    # Stock price line (secondary y-axis)
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["close_price"],
            name="Stock Price (₹)",
            line=dict(color="royalblue", width=2),
            mode="lines+markers"
        ),
        secondary_y=True
    )

    # Layout
    fig.update_layout(
        title=f"{stock_name} — Sentiment vs Stock Price",
        xaxis_title="Date",
        legend=dict(x=0, y=1.1, orientation="h"),
        plot_bgcolor="white",
        hovermode="x unified"
    )

    fig.update_yaxes(title_text="Sentiment Score (-1 to +1)", secondary_y=False)
    fig.update_yaxes(title_text="Stock Price (₹)", secondary_y=True)

    # Save as HTML
    output_path = f"data/{stock_name}_chart.html"
    fig.write_html(output_path)
    print(f"Chart saved: {output_path}")

    return fig

if __name__ == "__main__":
    stocks = ["Reliance Industries", "TCS", "Infosys", "HDFC Bank", "Wipro"]
    for stock in stocks:
        plot_stock(stock)