"""Event-driven backtesting engine for Taiwan stock strategies."""
from dataclasses import dataclass, field
from typing import Optional
import pandas as pd

from strategies.base_strategy import BaseStrategy, Signal
from data.fetcher import fetch_stock_data
from data.indicators import add_all_indicators
from .metrics import PerformanceMetrics, compute_metrics
from config import (
    INITIAL_CAPITAL, TOTAL_BUY_COST, TOTAL_SELL_COST,
    STOP_LOSS_PCT, TAKE_PROFIT_PCT, BACKTEST_PERIOD,
)


@dataclass
class Trade:
    symbol: str
    entry_date: str
    entry_price: float
    exit_date: Optional[str] = None
    exit_price: Optional[float] = None
    shares: int = 0
    pnl: float = 0.0
    return_pct: float = 0.0
    exit_reason: str = ""


@dataclass
class BacktestResult:
    strategy_name: str
    symbol: str
    period: str
    trades: list[Trade] = field(default_factory=list)
    metrics: Optional[PerformanceMetrics] = None

    def summary(self) -> str:
        lines = [f"[{self.strategy_name}] {self.symbol} ({self.period})"]
        if self.metrics:
            lines.append(self.metrics.summary())
        else:
            lines.append("  No metrics (no trades)")
        return "\n".join(lines)


class BacktestEngine:
    def __init__(self, initial_capital: float = INITIAL_CAPITAL):
        self.initial_capital = initial_capital

    def run(self, strategy: BaseStrategy, symbol: str,
            period: str = BACKTEST_PERIOD,
            indicator_params: dict = None) -> BacktestResult:
        """Run a single strategy on one symbol. Returns BacktestResult."""
        df = fetch_stock_data(symbol, period=period)
        if df is None or len(df) < 60:
            return BacktestResult(strategy.name, symbol, period)

        df = add_all_indicators(df, params=indicator_params)
        signals: list[Signal] = strategy.generate_signals(df, symbol)

        trades, equity_curve = self._simulate(df, signals)
        trade_returns = [t.return_pct for t in trades if t.exit_date]
        metrics = compute_metrics(trade_returns, equity_curve)

        result = BacktestResult(
            strategy_name=strategy.name,
            symbol=symbol,
            period=period,
            trades=trades,
            metrics=metrics,
        )
        return result

    def run_multi_symbol(self, strategy: BaseStrategy, symbols: list[str],
                         period: str = BACKTEST_PERIOD) -> list[BacktestResult]:
        return [self.run(strategy, sym, period) for sym in symbols]

    # ------------------------------------------------------------------ #
    def _simulate(self, df: pd.DataFrame, signals: list[Signal]
                  ) -> tuple[list[Trade], list[float]]:
        capital = self.initial_capital
        position: Optional[Trade] = None
        trades: list[Trade] = []
        equity_curve: list[float] = [capital]

        signal_map: dict[str, Signal] = {}
        for sig in signals:
            if sig.action in ("BUY", "SELL"):
                signal_map[sig.date] = sig  # last signal on that date wins

        for i, (idx, row) in enumerate(df.iterrows()):
            date = str(idx.date())
            price = row["Close"]

            # Check stop-loss / take-profit on open position
            if position:
                sl = position.entry_price * (1 - STOP_LOSS_PCT)
                tp = position.entry_price * (1 + TAKE_PROFIT_PCT)
                reason = None
                exit_price = price

                if row["Low"] <= sl:
                    reason = "stop_loss"
                    exit_price = sl
                elif row["High"] >= tp:
                    reason = "take_profit"
                    exit_price = tp

                if reason:
                    position = self._close_trade(position, date, exit_price, reason)
                    proceeds = position.shares * exit_price * (1 - TOTAL_SELL_COST)
                    capital += proceeds
                    trades.append(position)
                    position = None

            # Process signal for today
            sig = signal_map.get(date)
            if sig:
                if sig.action == "BUY" and position is None:
                    max_invest = capital * 0.10  # 10% per position
                    shares = int(max_invest / (price * (1 + TOTAL_BUY_COST)))
                    if shares > 0:
                        cost = shares * price * (1 + TOTAL_BUY_COST)
                        if cost <= capital:
                            capital -= cost
                            position = Trade(
                                symbol=sig.symbol,
                                entry_date=date,
                                entry_price=price,
                                shares=shares,
                            )

                elif sig.action == "SELL" and position is not None:
                    position = self._close_trade(position, date, price, "sell_signal")
                    proceeds = position.shares * price * (1 - TOTAL_SELL_COST)
                    capital += proceeds
                    trades.append(position)
                    position = None

            # Mark-to-market equity
            mtm = capital
            if position:
                mtm += position.shares * price
            equity_curve.append(mtm)

        # Close any open position at end
        if position:
            last_price = df["Close"].iloc[-1]
            last_date = str(df.index[-1].date())
            position = self._close_trade(position, last_date, last_price, "end_of_period")
            proceeds = position.shares * last_price * (1 - TOTAL_SELL_COST)
            capital += proceeds
            trades.append(position)
            equity_curve[-1] = capital

        return trades, equity_curve

    @staticmethod
    def _close_trade(trade: Trade, date: str, price: float, reason: str) -> Trade:
        trade.exit_date = date
        trade.exit_price = price
        gross_pnl = (price - trade.entry_price) * trade.shares
        cost = trade.entry_price * trade.shares * TOTAL_BUY_COST
        tax = price * trade.shares * TOTAL_SELL_COST
        trade.pnl = round(gross_pnl - cost - tax, 2)
        trade.return_pct = round(
            (price / trade.entry_price - 1) - TOTAL_BUY_COST - TOTAL_SELL_COST, 6
        )
        trade.exit_reason = reason
        return trade
