"""RSI 超賣反彈策略 (RSI oversold bounce strategy)."""
import pandas as pd
from .base_strategy import BaseStrategy, Signal, StrategyParams
from config import STOP_LOSS_PCT, TAKE_PROFIT_PCT


class RSIStrategy(BaseStrategy):
    """
    Buy when RSI exits oversold territory (crosses above oversold_threshold).
    Sell when RSI enters overbought territory (crosses above overbought_threshold).
    Uses MACD histogram direction as a confirmation filter.
    """

    @property
    def name(self) -> str:
        return "RSI_Strategy"

    @property
    def default_params(self) -> dict:
        return {
            "oversold": 30,
            "overbought": 70,
            "stop_loss_pct": STOP_LOSS_PCT,
            "take_profit_pct": TAKE_PROFIT_PCT,
            "confirm_macd": True,   # require MACD hist to be rising
            "min_vol_ratio": 1.0,   # prefer above-average volume on entry
        }

    def generate_signals(self, df: pd.DataFrame, symbol: str) -> list[Signal]:
        if "RSI" not in df.columns:
            return []

        signals = []
        oversold = self.get_param("oversold")
        overbought = self.get_param("overbought")
        sl_pct = self.get_param("stop_loss_pct")
        tp_pct = self.get_param("take_profit_pct")
        confirm_macd = self.get_param("confirm_macd")
        min_vol = self.get_param("min_vol_ratio")

        rsi = df["RSI"]

        for i in range(1, len(df)):
            row = df.iloc[i]
            prev_rsi = rsi.iloc[i - 1]
            curr_rsi = rsi.iloc[i]
            price = row["Close"]
            date = str(df.index[i].date())

            macd_ok = True
            if confirm_macd and "MACD_Hist" in df.columns:
                macd_ok = (row["MACD_Hist"] > df["MACD_Hist"].iloc[i - 1])

            # RSI bouncing out of oversold
            if prev_rsi <= oversold < curr_rsi and macd_ok:
                vol_ok = row.get("Vol_Ratio", 1.0) >= min_vol
                confidence = 0.6 + (0.2 if vol_ok else 0) + (0.1 if macd_ok else 0)
                confidence = min(1.0, confidence)
                signals.append(Signal(
                    date=date, symbol=symbol, action="BUY", price=price,
                    stop_loss=round(price * (1 - sl_pct), 2),
                    take_profit=round(price * (1 + tp_pct), 2),
                    confidence=round(confidence, 3),
                    reason=f"RSI bounce from oversold ({prev_rsi:.1f}→{curr_rsi:.1f})"
                ))

            # RSI entering overbought – exit signal
            elif prev_rsi < overbought <= curr_rsi:
                signals.append(Signal(
                    date=date, symbol=symbol, action="SELL", price=price,
                    stop_loss=0.0, take_profit=0.0,
                    confidence=0.65,
                    reason=f"RSI entered overbought ({curr_rsi:.1f})"
                ))

        return signals
