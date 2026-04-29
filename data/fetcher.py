import yfinance as yf
import pandas as pd
from typing import Optional


def fetch_stock_data(symbol: str, period: str = "1y", interval: str = "1d") -> Optional[pd.DataFrame]:
    """Fetch OHLCV data for a Taiwan stock symbol (e.g. '2330.TW')."""
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval, auto_adjust=True)
        if df.empty:
            return None
        df.index = pd.to_datetime(df.index).tz_localize(None)
        df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
        df.dropna(inplace=True)
        return df
    except Exception as e:
        print(f"[fetcher] Error fetching {symbol}: {e}")
        return None


def fetch_multiple(symbols: list[str], period: str = "1y") -> dict[str, pd.DataFrame]:
    """Fetch data for multiple symbols, skipping failed ones."""
    result = {}
    for sym in symbols:
        df = fetch_stock_data(sym, period=period)
        if df is not None and len(df) >= 60:
            result[sym] = df
    return result
