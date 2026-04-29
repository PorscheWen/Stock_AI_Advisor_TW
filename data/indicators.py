"""Technical indicators for Taiwan stock analysis."""
import pandas as pd
import numpy as np


def add_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    delta = df["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df["RSI"] = 100 - (100 / (1 + rs))
    return df


def add_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    ema_fast = df["Close"].ewm(span=fast, adjust=False).mean()
    ema_slow = df["Close"].ewm(span=slow, adjust=False).mean()
    df["MACD"] = ema_fast - ema_slow
    df["MACD_Signal"] = df["MACD"].ewm(span=signal, adjust=False).mean()
    df["MACD_Hist"] = df["MACD"] - df["MACD_Signal"]
    return df


def add_kd(df: pd.DataFrame, period: int = 9, smooth_k: int = 3, smooth_d: int = 3) -> pd.DataFrame:
    low_min = df["Low"].rolling(period).min()
    high_max = df["High"].rolling(period).max()
    raw_k = 100 * (df["Close"] - low_min) / (high_max - low_min).replace(0, np.nan)
    df["K"] = raw_k.ewm(com=smooth_k - 1, min_periods=smooth_k).mean()
    df["D"] = df["K"].ewm(com=smooth_d - 1, min_periods=smooth_d).mean()
    return df


def add_bollinger(df: pd.DataFrame, period: int = 20, std_mult: float = 2.0) -> pd.DataFrame:
    sma = df["Close"].rolling(period).mean()
    std = df["Close"].rolling(period).std()
    df["BB_Upper"] = sma + std_mult * std
    df["BB_Mid"] = sma
    df["BB_Lower"] = sma - std_mult * std
    df["BB_Width"] = (df["BB_Upper"] - df["BB_Lower"]) / df["BB_Mid"]
    return df


def add_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    high_low = df["High"] - df["Low"]
    high_close = (df["High"] - df["Close"].shift()).abs()
    low_close = (df["Low"] - df["Close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["ATR"] = tr.ewm(com=period - 1, min_periods=period).mean()
    return df


def add_volume_ma(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    df["Vol_MA"] = df["Volume"].rolling(period).mean()
    df["Vol_Ratio"] = df["Volume"] / df["Vol_MA"]
    return df


def add_ma(df: pd.DataFrame, periods: list[int] = [5, 10, 20, 60]) -> pd.DataFrame:
    for p in periods:
        df[f"MA{p}"] = df["Close"].rolling(p).mean()
    return df


def add_all_indicators(df: pd.DataFrame, params: dict = None) -> pd.DataFrame:
    """Add all indicators with optional custom parameters."""
    p = params or {}
    df = add_rsi(df, period=p.get("rsi_period", 14))
    df = add_macd(df,
                  fast=p.get("macd_fast", 12),
                  slow=p.get("macd_slow", 26),
                  signal=p.get("macd_signal", 9))
    df = add_kd(df,
                period=p.get("kd_period", 9),
                smooth_k=p.get("kd_smooth_k", 3),
                smooth_d=p.get("kd_smooth_d", 3))
    df = add_bollinger(df,
                       period=p.get("bb_period", 20),
                       std_mult=p.get("bb_std", 2.0))
    df = add_atr(df, period=p.get("atr_period", 14))
    df = add_volume_ma(df, period=p.get("vol_period", 20))
    df = add_ma(df)
    df.dropna(inplace=True)
    return df
