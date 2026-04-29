"""
Orchestrator — coordinates the full AI agent pipeline.

Flow:
  1. MarketAgent   → evaluate overall market conditions
  2. BacktestEngine → run all strategies on all symbols
  3. StrategyAgent  → propose per-strategy parameter updates
  4. RiskAgent      → assess risk for top signals
  5. LearningAgent  → run autonomous learning cycle
  6. Return combined report
"""
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from .market_agent import MarketAgent
from .strategy_agent import StrategyAgent
from .risk_agent import RiskAgent
from .learning_agent import LearningAgent
from backtesting.engine import BacktestEngine
from strategies.registry import get_all_strategies
from storage.store import (
    load_strategy_params, save_backtest_result, load_performance_history
)
from config import DEFAULT_SYMBOLS, INITIAL_CAPITAL, BACKTEST_PERIOD

console = Console()


class Orchestrator:
    """Coordinates all agents in the Taiwan stock AI advisory pipeline."""

    def __init__(self, symbols: list[str] = None, portfolio_value: float = INITIAL_CAPITAL):
        self.symbols = symbols or DEFAULT_SYMBOLS
        self.portfolio_value = portfolio_value
        self.market_agent = MarketAgent()
        self.strategy_agent = StrategyAgent()
        self.risk_agent = RiskAgent()
        self.learning_agent = LearningAgent()
        self.engine = BacktestEngine(initial_capital=portfolio_value)

    # ------------------------------------------------------------------ #
    def run_full_cycle(self, run_learning: bool = True) -> dict:
        """Execute the complete advisory cycle."""
        console.print(Panel("[bold cyan]台股 AI 策略顧問系統啟動[/bold cyan]", expand=False))

        # Step 1: Market analysis
        market_conditions = self._step_market_analysis()

        # Scale back trading if market unfavorable
        position_scale = market_conditions.get("recommended_position_scale", 1.0)

        # Step 2: Backtests
        backtest_results = self._step_backtests()

        # Step 3: Strategy parameter proposals
        proposals = self._step_strategy_proposals(backtest_results)

        # Step 4: Risk assessment on top signals
        risk_reports = self._step_risk_assessment(backtest_results)

        # Step 5: Learning cycle
        learning_result = {}
        if run_learning:
            learning_result = self._step_learning()

        # Compile report
        report = {
            "market_conditions": market_conditions,
            "position_scale": position_scale,
            "backtest_results": [r.summary() for r in backtest_results],
            "strategy_proposals": proposals,
            "risk_reports": risk_reports,
            "learning": learning_result,
        }
        self._display_final_report(report, backtest_results)
        return report

    # ------------------------------------------------------------------ #
    def _step_market_analysis(self) -> dict:
        console.print("\n[bold yellow]Step 1/5: 分析市場狀況...[/bold yellow]")
        conditions = self.market_agent.analyze(symbols=self.symbols[:3])

        trend_color = {"BULLISH": "green", "BEARISH": "red", "SIDEWAYS": "yellow"}.get(
            conditions.get("market_trend", ""), "white"
        )
        console.print(f"  市場趨勢: [{trend_color}]{conditions.get('market_trend')}[/{trend_color}]")
        console.print(f"  交易環境: {conditions.get('trading_environment')}")
        console.print(f"  建議倉位: {conditions.get('recommended_position_scale', 1.0)*100:.0f}%")
        for obs in conditions.get("key_observations", [])[:3]:
            console.print(f"  • {obs}")
        return conditions

    def _step_backtests(self) -> list:
        console.print("\n[bold yellow]Step 2/5: 執行回測...[/bold yellow]")
        strategy_params = load_strategy_params()
        strategies = get_all_strategies(strategy_params)
        results = []

        for strategy in strategies:
            for symbol in self.symbols:
                console.print(f"  回測 {strategy.name} × {symbol}...", end=" ")
                result = self.engine.run(strategy, symbol, period=BACKTEST_PERIOD)
                results.append(result)

                if result.metrics and result.metrics.num_trades > 0:
                    ret = result.metrics.total_return_pct
                    color = "green" if ret > 0 else "red"
                    console.print(f"[{color}]{ret:+.2f}%[/{color}], "
                                  f"Sharpe {result.metrics.sharpe_ratio:.2f}, "
                                  f"{result.metrics.num_trades}筆交易")
                    # Persist to storage
                    save_backtest_result(
                        strategy.name, symbol,
                        result.metrics.to_dict(), BACKTEST_PERIOD
                    )
                else:
                    console.print("[dim]無交易[/dim]")
        return results

    def _step_strategy_proposals(self, results: list) -> list:
        console.print("\n[bold yellow]Step 3/5: 策略參數優化建議...[/bold yellow]")
        proposals = []
        strategy_params = load_strategy_params()
        perf_history = load_performance_history()

        # One proposal per strategy (use first symbol result with trades)
        seen = set()
        for result in results:
            name = result.strategy_name
            if name in seen:
                continue
            if not result.metrics or result.metrics.num_trades == 0:
                continue
            seen.add(name)

            sp = strategy_params.get(name)
            current = sp.params if sp else {}
            key = f"{name}:{result.symbol}"
            history = perf_history.get(key, [])

            console.print(f"  分析 {name}...", end=" ")
            proposal = self.strategy_agent.propose_update(result, current, history)
            proposals.append(proposal)

            confidence = proposal.get("confidence", 0)
            console.print(f"信心度 {confidence:.0%}, 建議: {list(proposal.get('parameter_updates', {}).keys())}")
        return proposals

    def _step_risk_assessment(self, results: list) -> list:
        console.print("\n[bold yellow]Step 4/5: 風險評估...[/bold yellow]")
        risk_reports = []

        # Assess risk for the top-performing result per symbol
        best_per_symbol: dict[str, object] = {}
        for result in results:
            if not result.metrics or result.metrics.num_trades == 0:
                continue
            sym = result.symbol
            existing = best_per_symbol.get(sym)
            if (existing is None or
                    result.metrics.sharpe_ratio > existing.metrics.sharpe_ratio):
                best_per_symbol[sym] = result

        for symbol, result in best_per_symbol.items():
            console.print(f"  評估 {symbol}...", end=" ")
            # Use the last trade's entry price for demonstration
            last_trade = next(
                (t for t in reversed(result.trades) if t.entry_price), None
            )
            if not last_trade:
                console.print("[dim]無交易記錄[/dim]")
                continue

            from data.fetcher import fetch_stock_data
            from data.indicators import add_all_indicators
            df = fetch_stock_data(symbol, period="3mo")
            if df is None or len(df) < 20:
                console.print("[dim]無法取得數據[/dim]")
                continue
            df = add_all_indicators(df)

            report = self.risk_agent.assess(
                symbol, last_trade.entry_price, df, self.portfolio_value
            )
            risk_reports.append(report)
            level_color = {"LOW": "green", "MEDIUM": "yellow", "HIGH": "red"}.get(
                report.get("risk_level", ""), "white"
            )
            console.print(
                f"[{level_color}]{report.get('risk_level')}[/{level_color}] — "
                f"{report.get('action_recommendation')}"
            )
        return risk_reports

    def _step_learning(self) -> dict:
        console.print("\n[bold yellow]Step 5/5: 自主學習循環...[/bold yellow]")
        result = self.learning_agent.run_learning_cycle()

        if result.get("status") == "ok":
            applied = result.get("applied_updates", [])
            console.print(f"  已更新 {len(applied)} 個策略參數")
            for upd in applied:
                console.print(
                    f"  ✓ {upd['strategy']} v{upd['new_version']}: {list(upd['updates'].keys())}"
                )
            insights = result.get("insights", [])
            if insights:
                console.print("  學習心得:")
                for insight in insights[:3]:
                    console.print(f"  • {insight}")
        else:
            console.print(f"  [{result.get('status')}] {result.get('reason', '')}")
        return result

    # ------------------------------------------------------------------ #
    def _display_final_report(self, report: dict, results: list):
        console.print("\n")
        console.print(Panel("[bold green]== 回測績效總覽 ==[/bold green]", expand=False))

        table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
        table.add_column("策略", style="cyan")
        table.add_column("標的")
        table.add_column("報酬率", justify="right")
        table.add_column("Sharpe", justify="right")
        table.add_column("回撤", justify="right")
        table.add_column("勝率", justify="right")
        table.add_column("交易次數", justify="right")

        for result in sorted(
            results,
            key=lambda r: r.metrics.sharpe_ratio if r.metrics else -999,
            reverse=True,
        ):
            if not result.metrics or result.metrics.num_trades == 0:
                continue
            m = result.metrics
            ret_color = "green" if m.total_return_pct > 0 else "red"
            table.add_row(
                result.strategy_name,
                result.symbol,
                f"[{ret_color}]{m.total_return_pct:+.2f}%[/{ret_color}]",
                f"{m.sharpe_ratio:.3f}",
                f"{m.max_drawdown_pct:.2f}%",
                f"{m.win_rate_pct:.1f}%",
                str(m.num_trades),
            )
        console.print(table)

        # Learning summary
        learning = report.get("learning", {})
        if learning.get("status") == "ok" and learning.get("analysis_summary"):
            console.print(Panel(
                learning["analysis_summary"],
                title="[bold blue]AI 學習分析摘要[/bold blue]",
                expand=False,
            ))
            next_focus = learning.get("next_focus", "")
            if next_focus:
                console.print(f"\n[dim]下次學習重點：{next_focus}[/dim]")
