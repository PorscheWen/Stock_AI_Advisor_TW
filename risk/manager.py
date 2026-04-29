"""Risk management utilities."""
import pandas as pd
import numpy as np
from dataclasses import dataclass
from config import (
    MAX_POSITION_PCT, STOP_LOSS_PCT, TAKE_PROFIT_PCT, MAX_DRAWDOWN_LIMIT
)


@dataclass
class RiskAssessment:
    symbol: str
    position_size_pct: float      # % of portfolio to allocate
    suggested_stop_loss: float    # price level
    suggested_take_profit: float  # price level
    risk_reward_ratio: float
    risk_level: str               # "LOW" | "MEDIUM" | "HIGH"
    warnings: list[str]


def assess_position_risk(
    symbol: str,
    entry_price: float,
    df: pd.DataFrame,
    portfolio_value: float,
    existing_positions: int = 0,
    volatility_scale: bool = True,
) -> RiskAssessment:
    """
    Calculate position size and risk levels using ATR-based sizing.
    Taiwan market context: 漲跌幅限制 ±10% daily limit.
    """
    warnings: list[str] = []

    # ATR-based stop loss (more adaptive than fixed %)
    atr = df["ATR"].iloc[-1] if "ATR" in df.columns else entry_price * 0.02
    atr_stop_pct = (atr / entry_price) * 1.5   # 1.5x ATR as stop
    sl_pct = max(atr_stop_pct, STOP_LOSS_PCT)   # never tighter than config minimum

    stop_loss = round(entry_price * (1 - sl_pct), 2)
    take_profit = round(entry_price * (1 + TAKE_PROFIT_PCT), 2)
    risk_reward = TAKE_PROFIT_PCT / sl_pct

    # Volatility-adjusted position sizing: risk 1% of portfolio per trade
    risk_per_trade = portfolio_value * 0.01   # risk 1% of portfolio
    risk_per_share = entry_price * sl_pct
    max_shares_by_risk = int(risk_per_trade / risk_per_share) if risk_per_share > 0 else 0

    # Also cap by MAX_POSITION_PCT
    max_invest = portfolio_value * MAX_POSITION_PCT
    max_shares_by_capital = int(max_invest / entry_price)

    shares = min(max_shares_by_risk, max_shares_by_capital)
    position_size_pct = (shares * entry_price / portfolio_value) * 100 if portfolio_value > 0 else 0

    # Diversification warning
    if existing_positions >= 5:
        warnings.append("Portfolio已有5個以上持倉，建議謹慎增加新部位")

    # Concentration warning
    if position_size_pct > 8:
        warnings.append(f"單筆倉位{position_size_pct:.1f}%，接近10%上限")

    # Low risk-reward warning
    if risk_reward < 1.5:
        warnings.append(f"風險報酬比{risk_reward:.2f}偏低（建議≥2.0）")
        risk_level = "HIGH"
    elif risk_reward >= 2.5:
        risk_level = "LOW"
    else:
        risk_level = "MEDIUM"

    # Check recent volatility
    if "ATR" in df.columns:
        recent_vol = (df["ATR"].iloc[-5:].mean() / df["Close"].iloc[-5:].mean()) * 100
        if recent_vol > 3.0:
            warnings.append(f"近期波動率偏高({recent_vol:.1f}%)，考慮縮小部位")
            risk_level = "HIGH"

    return RiskAssessment(
        symbol=symbol,
        position_size_pct=round(position_size_pct, 2),
        suggested_stop_loss=stop_loss,
        suggested_take_profit=take_profit,
        risk_reward_ratio=round(risk_reward, 2),
        risk_level=risk_level,
        warnings=warnings,
    )


def check_portfolio_risk(equity_curve: list[float]) -> dict:
    """Check if current portfolio drawdown exceeds limit."""
    if len(equity_curve) < 2:
        return {"ok": True, "drawdown_pct": 0.0}

    arr = np.array(equity_curve)
    running_max = np.maximum.accumulate(arr)
    current_dd = (arr[-1] - running_max[-1]) / running_max[-1]
    dd_pct = abs(current_dd) * 100

    return {
        "ok": dd_pct < MAX_DRAWDOWN_LIMIT * 100,
        "drawdown_pct": round(dd_pct, 2),
        "limit_pct": MAX_DRAWDOWN_LIMIT * 100,
    }
