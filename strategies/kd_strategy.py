"""KD 黃金交叉 / 死亡交叉策略 (KD cross strategy for Taiwan stocks)."""
import pandas as pd
from .base_strategy import BaseStrategy, Signal, StrategyParams
from config import STOP_LOSS_PCT, TAKE_PROFIT_PCT


class KDStrategy(BaseStrategy):
    """
    Buy when K crosses above D from oversold zone (K < oversold_threshold).
    Sell when K crosses below D from overbought zone (K > overbought_threshold).
    """

    @property
    def name(self) -> str:
        return "KD_Strategy"

    @property
    def default_params(self) -> dict:
        return {
            "oversold": 25,
            "overbought": 75,
            "stop_loss_pct": STOP_LOSS_PCT,
            "take_profit_pct": TAKE_PROFIT_PCT,
            "min_vol_ratio": 0.8,   # minimum volume ratio vs 20-day average
        }

    def generate_signals(self, df: pd.DataFrame, symbol: str) -> list[Signal]:
        required = ["K", "D", "Vol_Ratio"]
        if not all(c in df.columns for c in required):
            return []

        signals = []
        oversold = self.get_param("oversold")
        overbought = self.get_param("overbought")
        sl_pct = self.get_param("stop_loss_pct")
        tp_pct = self.get_param("take_profit_pct")
        min_vol = self.get_param("min_vol_ratio")

        k = df["K"]
        d = df["D"]

        for i in range(1, len(df)):
            row = df.iloc[i]
            prev_k = k.iloc[i - 1]
            prev_d = d.iloc[i - 1]
            curr_k = k.iloc[i]
            curr_d = d.iloc[i]
            price = row["Close"]
            date = str(df.index[i].date())

            # Golden cross from oversold: K crosses above D when both < oversold
            if (prev_k < prev_d and curr_k > curr_d
                    and curr_k < oversold
                    and row.get("Vol_Ratio", 1.0) >= min_vol):
                confidence = min(1.0, (oversold - curr_k) / oversold + 0.4)
                signals.append(Signal(
                    date=date, symbol=symbol, action="BUY", price=price,
                    stop_loss=round(price * (1 - sl_pct), 2),
                    take_profit=round(price * (1 + tp_pct), 2),
                    confidence=round(confidence, 3),
                    reason=f"KD golden cross (K={curr_k:.1f}, D={curr_d:.1f}) in oversold zone"
                ))

            # Death cross from overbought: K crosses below D when both > overbought
            elif (prev_k > prev_d and curr_k < curr_d
                    and curr_k > overbought):
                signals.append(Signal(
                    date=date, symbol=symbol, action="SELL", price=price,
                    stop_loss=0.0, take_profit=0.0,
                    confidence=0.7,
                    reason=f"KD death cross (K={curr_k:.1f}, D={curr_d:.1f}) in overbought zone"
                ))

        return signals
