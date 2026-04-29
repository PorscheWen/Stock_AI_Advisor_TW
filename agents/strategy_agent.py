"""Strategy analysis agent — proposes parameter refinements based on backtest results."""
import json
from .base_agent import BaseAgent
from backtesting.engine import BacktestResult

_SYSTEM = """你是一位量化交易策略優化專家。你的職責是分析回測績效指標，
找出策略的弱點和改善機會，並提出具體的參數調整建議。
你熟悉台股市場特性：每日±10%漲跌限制、流動性特點、季報效應等。
你的建議必須保守且有依據，避免過度擬合歷史數據。"""

_TOOLS = [
    {
        "name": "propose_parameter_update",
        "description": "提出策略參數更新建議",
        "input_schema": {
            "type": "object",
            "properties": {
                "strategy_name": {
                    "type": "string",
                    "description": "策略名稱"
                },
                "parameter_updates": {
                    "type": "object",
                    "description": "建議更新的參數鍵值對，例如 {\"rsi_oversold\": 28, \"rsi_overbought\": 72}"
                },
                "rationale": {
                    "type": "string",
                    "description": "調整原因的詳細說明"
                },
                "expected_improvement": {
                    "type": "string",
                    "description": "預期改善的指標和幅度"
                },
                "confidence": {
                    "type": "number",
                    "description": "建議信心度 0.0-1.0"
                },
            },
            "required": ["strategy_name", "parameter_updates", "rationale",
                         "expected_improvement", "confidence"],
        },
    }
]


class StrategyAgent(BaseAgent):
    """Analyzes backtest results and proposes strategy parameter updates."""

    def __init__(self):
        super().__init__("StrategyAgent", _SYSTEM)

    def propose_update(
        self,
        result: BacktestResult,
        current_params: dict,
        history: list[dict] = None,
    ) -> dict:
        """
        Given a BacktestResult and current params, returns a parameter update proposal.
        history: list of previous performance dicts for trend analysis.
        """
        prompt = self._build_prompt(result, current_params, history or [])
        response = self._call(
            prompt,
            tools=_TOOLS,
            tool_choice={"type": "tool", "name": "propose_parameter_update"},
            max_tokens=4096,
        )
        proposal = self._extract_tool_input(response, "propose_parameter_update")
        if not proposal:
            return {"strategy_name": result.strategy_name, "parameter_updates": {},
                    "rationale": "無法生成建議", "expected_improvement": "N/A", "confidence": 0.0}
        return proposal

    # ------------------------------------------------------------------ #
    def _build_prompt(self, result: BacktestResult, current_params: dict,
                      history: list[dict]) -> str:
        m = result.metrics
        lines = [
            f"## 策略：{result.strategy_name}  標的：{result.symbol}  期間：{result.period}",
            "",
            "### 當前回測績效",
        ]
        if m:
            lines += [
                f"- 總報酬率: {m.total_return_pct:+.2f}%",
                f"- 年化報酬率: {m.annualized_return_pct:+.2f}%",
                f"- Sharpe Ratio: {m.sharpe_ratio:.3f}",
                f"- Sortino Ratio: {m.sortino_ratio:.3f}",
                f"- 最大回撤: {m.max_drawdown_pct:.2f}%",
                f"- 勝率: {m.win_rate_pct:.1f}%",
                f"- 獲利因子: {m.profit_factor:.2f}",
                f"- 交易次數: {m.num_trades}",
                f"- 平均每筆報酬: {m.avg_trade_return_pct:+.2f}%",
            ]
        else:
            lines.append("- 無交易，策略未能產生訊號")

        lines += ["", "### 當前策略參數"]
        lines.append(json.dumps(current_params, ensure_ascii=False, indent=2))

        if history:
            lines += ["", "### 歷史績效趨勢（最近數次）"]
            for i, h in enumerate(history[-4:], 1):
                metrics = h.get("metrics", {})
                lines.append(
                    f"  第{i}次: 報酬{metrics.get('total_return_pct', 0):+.2f}%, "
                    f"Sharpe {metrics.get('sharpe_ratio', 0):.3f}, "
                    f"回撤 {metrics.get('max_drawdown_pct', 0):.2f}%"
                )

        lines += [
            "",
            "### 任務",
            "請分析上述績效，找出最主要的問題（例如：勝率低、回撤大、訊號太少/太多），",
            "提出2-3個具體的參數調整建議。確保調整幅度保守（每次不超過20%的相對變動）。",
            "呼叫 propose_parameter_update 工具提交建議。",
        ]
        return "\n".join(lines)
