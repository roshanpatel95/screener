import yfinance as yf
import pandas as pd
import requests
import numpy as np # Import numpy for NaN checks

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
    df['EMA200'] = df['Close'].ewm(span=200, adjust=False).mean() # Added adjust=False for standard EMA
    return df

def check_detachment(ticker):
    df = fetch_data(ticker)
    
    # Check if df is empty or required columns are missing
    if df.empty or 'Close' not in df.columns or 'EMA200' not in df.columns:
        print(f"Skipping {ticker}: Dataframe is empty or missing required columns.")
        return None

    latest = df.iloc[-1]
    close = latest['Close']
    ema200 = latest['EMA200']
    
    # Check for NaN values in close or ema200
    if pd.isna(close) or pd.isna(ema200):
        print(f"Skipping {ticker}: Latest Close or EMA200 is NaN. (Close: {close}, EMA200: {ema200})")
        return None

    # Check for zero in ema200 to avoid division by zero
    if ema200 == 0:
        print(f"Skipping {ticker}: EMA200 is zero, cannot calculate detachment.")
        return None

    # Ensure these are scalar values if there's any ambiguity,
    # though direct access like this usually works for single elements of a Series.
    # The previous error likely stemmed from NaNs, not Series ambiguity,
    # but explicit float conversion after NaN check is harmless.
    try:
        detachment = float(abs(close - ema200) / ema200)
    except TypeError: # Catch any remaining type issues during conversion
        print(f"Skipping {ticker}: Type error during detachment calculation. (Close: {close}, EMA200: {ema200})")
        return None
    except ZeroDivisionError:
        print(f"Skipping {ticker}: Division by zero during detachment calculation (EMA200 was zero).")
        return None


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
