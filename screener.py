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
    # Added threads=False to yf.download to potentially avoid some issues
    # and also show auto_adjust=True explicitly for clarity (though it's default now)
    df = yf.download(ticker, period="250d", interval="1d", threads=False, auto_adjust=True)
    df['EMA200'] = df['Close'].ewm(span=200, adjust=False).mean() # Added adjust=False for standard EMA
    return df

def check_detachment(ticker):
    df = fetch_data(ticker)
    
    # Check if df is empty or required columns are missing
    if df.empty or 'Close' not in df.columns or 'EMA200' not in df.columns:
        print(f"Skipping {ticker}: Dataframe is empty or missing required columns ('Close' or 'EMA200').")
        return None

    # Ensure there's at least one row of data to get the latest
    if len(df) == 0:
        print(f"Skipping {ticker}: No data available in dataframe.")
        return None

    latest = df.iloc[-1]
    
    # *** CRUCIAL CHANGE: Use .item() to extract scalar values ***
    try:
        close = latest['Close'].item()
        ema200 = latest['EMA200'].item()
    except ValueError: # Catches if .item() fails (e.g., if the Series has more than one item, though unlikely here)
        print(f"Skipping {ticker}: Could not extract scalar values for Close or EMA200.")
        return None
    except KeyError: # Catches if 'Close' or 'EMA200' columns are missing in latest Series (should be caught by earlier check, but good safeguard)
        print(f"Skipping {ticker}: 'Close' or 'EMA200' column not found in latest data for {ticker}.")
        return None

    # Check for NaN values in close or ema200
    if pd.isna(close) or pd.isna(ema200):
        print(f"Skipping {ticker}: Latest Close or EMA200 is NaN. (Close: {close}, EMA200: {ema200})")
        return None

    # Check for zero in ema200 to avoid division by zero
    if ema200 == 0:
        print(f"Skipping {ticker}: EMA200 is zero, cannot calculate detachment for {ticker}.")
        return None

    try:
        detachment = abs(close - ema200) / ema200
    except ZeroDivisionError:
        print(f"Skipping {ticker}: Division by zero during detachment calculation (EMA200 was zero).")
        return None
    
    # No need to cast to float here, as .item() already ensures it's a scalar.
    # The comparison `detachment > DETACH_THRESHOLD` will now work correctly.

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
    # Check for non-2xx status codes for better error reporting
    if not response.ok:
        print(f"ERROR: Discord webhook failed with status code {response.status_code}: {response.text}")
    return response.status_code

def run_screener():
    for ticker in TICKERS:
        alert = check_detachment(ticker)
        if alert:
            print(alert)
            send_discord_alert(alert)

if __name__ == "__main__":
    run_screener()
