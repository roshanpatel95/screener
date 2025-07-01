import yfinance as yf
import pandas as pd
import requests

# --- CONFIG ---
TICKERS = [
    "AAPL", "AMD", "AMZN", "AVGO", "BABA", "BRK.B", "COST", "CRWV", "GOOGL",
    "JNJ", "JPM", "KO", "LLY", "META", "MSFT", "NFLX", "NVDA", "ORCL", "PG",
    "PLTR", "QQQ", "RDDT", "SPY", "TSLA", "TSM", "UNH", "V", "WMT", "XOM"
]
DETACH_THRESHOLD = 0.01 / 100  # 0.01%
DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1389683227886882888/WS5YJSmGZtQb9zLtVfipeKoHArMa-IWMfxrcYLUBiPRmdkRU7lAskoW9K33aUdP8MfOS"  # replace with yours

def fetch_data(ticker):
    df = yf.download(ticker, period="250d", interval="1d")
    df['EMA200'] = df['Close'].ewm(span=200).mean()
    return df

def check_detachment(ticker):
    df = fetch_data(ticker)
    if df.empty or 'EMA200' not in df.columns: # Changed to df.columns for clarity
        return None

    latest = df.iloc[-1]
    # Ensure these are scalar values using .item() if there's any ambiguity,
    # though direct access like this usually works for single elements of a Series.
    close = latest['Close']
    ema200 = latest['EMA200']
    
    # Explicitly convert to float to prevent any Series-like behavior
    detachment = float(abs(close - ema200) / ema200)

    if detachment > DETACH_THRESHOLD:
        direction = "above" if close > ema200 else "below"
        percent = round(detachment * 100, 4)
        return f"{ticker} is {direction} the 200 EMA by {percent}% (Close: {close:.2f}, EMA200: {ema200:.2f})"
    return None

def send_discord_alert(message):
    data = {"content": message}
    response = requests.post(DISCORD_WEBHOOK, json=data)
    # Print status code for debugging in GitHub Actions logs
    print(f"Discord alert sent with status code: {response.status_code}") 
    return response.status_code

def run_screener():
    for ticker in TICKERS:
        alert = check_detachment(ticker)
        if alert:
            print(alert)
            send_discord_alert(alert)

if __name__ == "__main__":
    run_screener()
