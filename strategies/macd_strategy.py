"""MACD 趨勢動能策略 (MACD trend momentum strategy)."""
import pandas as pd
from .base_strategy import BaseStrategy, Signal, StrategyParams
from config import STOP_LOSS_PCT, TAKE_PROFIT_PCT


class MACDStrategy(BaseStrategy):
    """
    Buy when MACD histogram flips from negative to positive AND
    MACD line is above/near zero with rising volume.
    Sell when histogram flips back negative or price hits target/stop.
    """

    @property
    def name(self) -> str:
        return "MACD_Strategy"

    @property
    def default_params(self) -> dict:
        return {
            "stop_loss_pct": STOP_LOSS_PCT,
            "take_profit_pct": TAKE_PROFIT_PCT,
            "require_macd_above_zero": False,  # stricter filter: MACD > 0
            "min_vol_ratio": 1.1,              # volume must be above average
            "hist_consecutive": 1,             # bars histogram must be positive before buy
        }

    def generate_signals(self, df: pd.DataFrame, symbol: str) -> list[Signal]:
        required = ["MACD", "MACD_Signal", "MACD_Hist"]
        if not all(c in df.columns for c in required):
            return []

        signals = []
        sl_pct = self.get_param("stop_loss_pct")
        tp_pct = self.get_param("take_profit_pct")
        above_zero = self.get_param("require_macd_above_zero")
        min_vol = self.get_param("min_vol_ratio")
        consec = max(1, self.get_param("hist_consecutive"))

        hist = df["MACD_Hist"]

        for i in range(consec, len(df)):
            row = df.iloc[i]
            price = row["Close"]
            date = str(df.index[i].date())
            curr_hist = hist.iloc[i]
            prev_hist = hist.iloc[i - 1]

            vol_ok = row.get("Vol_Ratio", 1.0) >= min_vol
            zero_ok = (not above_zero) or (row["MACD"] > 0)

            # Histogram crosses zero from below (bearish → bullish)
            if prev_hist < 0 < curr_hist and vol_ok and zero_ok:
                # All preceding `consec` bars must also be positive (already guaranteed for consec=1)
                confidence = 0.55 + (0.15 if vol_ok else 0) + (0.10 if zero_ok else 0)
                signals.append(Signal(
                    date=date, symbol=symbol, action="BUY", price=price,
                    stop_loss=round(price * (1 - sl_pct), 2),
                    take_profit=round(price * (1 + tp_pct), 2),
                    confidence=round(min(1.0, confidence), 3),
                    reason=f"MACD hist crossed positive (MACD={row['MACD']:.4f})"
                ))

            # Histogram crosses zero from above (bullish → bearish)
            elif prev_hist > 0 > curr_hist:
                signals.append(Signal(
                    date=date, symbol=symbol, action="SELL", price=price,
                    stop_loss=0.0, take_profit=0.0,
                    confidence=0.60,
                    reason=f"MACD hist turned negative (MACD={row['MACD']:.4f})"
                ))

        return signals
