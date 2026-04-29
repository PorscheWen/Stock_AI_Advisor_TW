"""Performance metrics for backtest results."""
import numpy as np
import pandas as pd
from dataclasses import dataclass, asdict


@dataclass
class PerformanceMetrics:
    total_return_pct: float
    annualized_return_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown_pct: float
    win_rate_pct: float
    profit_factor: float
    num_trades: int
    avg_trade_return_pct: float
    avg_win_pct: float
    avg_loss_pct: float
    calmar_ratio: float

    def to_dict(self) -> dict:
        return asdict(self)

    def summary(self) -> str:
        lines = [
            f"  總報酬率        : {self.total_return_pct:+.2f}%",
            f"  年化報酬率      : {self.annualized_return_pct:+.2f}%",
            f"  Sharpe Ratio   : {self.sharpe_ratio:.3f}",
            f"  Sortino Ratio  : {self.sortino_ratio:.3f}",
            f"  最大回撤        : {self.max_drawdown_pct:.2f}%",
            f"  勝率            : {self.win_rate_pct:.1f}%",
            f"  獲利因子        : {self.profit_factor:.2f}",
            f"  交易次數        : {self.num_trades}",
            f"  平均每筆報酬    : {self.avg_trade_return_pct:+.2f}%",
            f"  平均獲利        : {self.avg_win_pct:+.2f}%",
            f"  平均虧損        : {self.avg_loss_pct:+.2f}%",
            f"  Calmar Ratio   : {self.calmar_ratio:.3f}",
        ]
        return "\n".join(lines)


def compute_metrics(trade_returns: list[float], equity_curve: list[float],
                    trading_days: int = 252) -> PerformanceMetrics:
    """
    trade_returns: list of percentage returns per closed trade (e.g. 0.05 = +5%)
    equity_curve:  list of portfolio values over time (daily)
    """
    if not trade_returns or not equity_curve:
        return _empty_metrics()

    returns_arr = np.array(trade_returns)
    equity_arr = np.array(equity_curve, dtype=float)

    # Total & annualized return
    total_ret = (equity_arr[-1] / equity_arr[0] - 1) * 100
    n_days = max(len(equity_arr), 1)
    ann_ret = ((equity_arr[-1] / equity_arr[0]) ** (trading_days / n_days) - 1) * 100

    # Daily returns from equity curve
    daily_rets = np.diff(equity_arr) / equity_arr[:-1]
    mean_daily = daily_rets.mean()
    std_daily = daily_rets.std()

    sharpe = (mean_daily / std_daily * np.sqrt(trading_days)) if std_daily > 0 else 0.0

    # Sortino (downside deviation)
    neg_rets = daily_rets[daily_rets < 0]
    down_std = neg_rets.std() if len(neg_rets) > 1 else 1e-9
    sortino = (mean_daily / down_std * np.sqrt(trading_days)) if down_std > 0 else 0.0

    # Max drawdown
    running_max = np.maximum.accumulate(equity_arr)
    drawdowns = (equity_arr - running_max) / running_max
    max_dd = abs(drawdowns.min()) * 100

    # Win/loss stats from trade returns
    wins = returns_arr[returns_arr > 0]
    losses = returns_arr[returns_arr <= 0]
    win_rate = len(wins) / len(returns_arr) * 100 if len(returns_arr) > 0 else 0
    avg_win = wins.mean() * 100 if len(wins) > 0 else 0.0
    avg_loss = losses.mean() * 100 if len(losses) > 0 else 0.0
    avg_trade = returns_arr.mean() * 100

    total_profit = wins.sum() if len(wins) > 0 else 0.0
    total_loss = abs(losses.sum()) if len(losses) > 0 else 1e-9
    profit_factor = total_profit / total_loss if total_loss > 0 else float("inf")

    calmar = ann_ret / max_dd if max_dd > 0 else 0.0

    return PerformanceMetrics(
        total_return_pct=round(total_ret, 3),
        annualized_return_pct=round(ann_ret, 3),
        sharpe_ratio=round(sharpe, 4),
        sortino_ratio=round(sortino, 4),
        max_drawdown_pct=round(max_dd, 3),
        win_rate_pct=round(win_rate, 2),
        profit_factor=round(profit_factor, 4),
        num_trades=len(returns_arr),
        avg_trade_return_pct=round(avg_trade, 3),
        avg_win_pct=round(avg_win, 3),
        avg_loss_pct=round(avg_loss, 3),
        calmar_ratio=round(calmar, 4),
    )


def _empty_metrics() -> PerformanceMetrics:
    return PerformanceMetrics(
        total_return_pct=0.0, annualized_return_pct=0.0, sharpe_ratio=0.0,
        sortino_ratio=0.0, max_drawdown_pct=0.0, win_rate_pct=0.0,
        profit_factor=0.0, num_trades=0, avg_trade_return_pct=0.0,
        avg_win_pct=0.0, avg_loss_pct=0.0, calmar_ratio=0.0,
    )
