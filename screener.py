import yfinance as yf
import pandas as pd
import requests
import numpy as np
import datetime

# --- CONFIG ---
TICKERS = [
    "AAPL", "AMD", "AMZN", "AVGO", "BABA", "BRK.B", "COST", "CRWV", "GOOGL",
    "JNJ", "JPM", "KO", "LLY", "META", "MSFT", "NFLX", "NVDA", "ORCL", "PG",
    "PLTR", "QQQ", "RDDT", "SPY", "TSLA", "TSM", "UNH", "V", "WMT", "XOM"
]
# DETACH_THRESHOLD defines what "touching" means.
# A stock is 'touching' if its detachment percentage is <= DETACH_THRESHOLD
DETACH_THRESHOLD = 0.01 / 100  # 0.01%
DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1389683227886882888/WS5YJSmGZtQb9zLtVfipeKoHArMa-IWMfxrcYLUBiPRmdkRU7lAskoW9K33aUdP8MfOS"  # replace with yours

def fetch_data(ticker):
    # Fetch enough data to cover 200 EMA + at least 2 extra days for current/previous day check
    # 250d is usually enough, but let's be safe.
    df = yf.download(ticker, period="250d", interval="1d", threads=False, auto_adjust=True)
    df['EMA200'] = df['Close'].ewm(span=200, adjust=False).mean()
    return df

def calculate_detachment(close, ema200):
    """Calculates the absolute percentage detachment."""
    if pd.isna(close) or pd.isna(ema200) or ema200 == 0:
        return np.nan # Return NaN if values are invalid

    return abs(close - ema200) / ema200

def check_just_detached(ticker):
    df = fetch_data(ticker)

    # Check for empty dataframe or missing columns
    if df.empty or 'Close' not in df.columns or 'EMA200' not in df.columns:
        print(f"Skipping {ticker}: Dataframe is empty or missing required columns ('Close' or 'EMA200').")
        return None

    # Ensure there's enough data for today and yesterday
    if len(df) < 2:
        print(f"Skipping {ticker}: Not enough data for today and yesterday. (Rows: {len(df)})")
        return None

    # Get today's and yesterday's data
    today_data = df.iloc[-1]
    yesterday_data = df.iloc[-2]

    # Extract scalar values using .item()
    try:
        today_close = today_data['Close'].item()
        today_ema200 = today_data['EMA200'].item()
        yesterday_close = yesterday_data['Close'].item()
        yesterday_ema200 = yesterday_data['EMA200'].item()
    except (ValueError, KeyError) as e:
        print(f"Skipping {ticker}: Could not extract scalar values for Close or EMA200 from latest data. Error: {e}")
        return None

    # Calculate detachments
    today_detachment = calculate_detachment(today_close, today_ema200)
    yesterday_detachment = calculate_detachment(yesterday_close, yesterday_ema200)

    # Check for NaN detachments (means there was an issue with close/ema200 for that day)
    if pd.isna(today_detachment) or pd.isna(yesterday_detachment):
        print(f"Skipping {ticker}: Detachment could not be calculated for today or yesterday due to invalid data.")
        return None

    # Condition: Was it touching yesterday AND is it detached today?
    was_touching_yesterday = yesterday_detachment <= DETACH_THRESHOLD
    is_detached_today = today_detachment > DETACH_THRESHOLD

    if was_touching_yesterday and is_detached_today:
        direction = "above" if today_close > today_ema200 else "below"
        percent = round(today_detachment * 100, 4)
        return (f"{ticker} JUST DETACHED {direction} the 200 EMA by {percent}% "
                f"(Today: {today_close:.2f}, EMA200: {today_ema200:.2f}, "
                f"Yesterday: {yesterday_close:.2f}, Yest EMA200: {yesterday_ema200:.2f})")
    
    return None

def send_discord_alert(message):
    data = {"content": message}
    response = requests.post(DISCORD_WEBHOOK, json=data)
    print(f"Discord alert sent with status code: {response.status_code}")
    if not response.ok:
        print(f"ERROR: Discord webhook failed with status code {response.status_code}: {response.text}")
    return response.status_code

def run_screener():
    print(f"Running screener at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    found_alerts = False
    for ticker in TICKERS:
        alert = check_just_detached(ticker) # Renamed function
        if alert:
            print(alert)
            send_discord_alert(alert)
            found_alerts = True
    if not found_alerts:
        print("No new detachments found today.")
        send_discord_alert("Daily EMA Screener: No new detachments found today.") # Optional: send a "no alerts" message

if __name__ == "__main__":
    run_screener()
