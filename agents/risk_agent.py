"""Risk assessment agent — wraps risk/manager.py with Claude narrative evaluation."""
import json
import pandas as pd
from .base_agent import BaseAgent
from risk.manager import assess_position_risk, check_portfolio_risk, RiskAssessment

_SYSTEM = """你是一位專業的風險管理顧問，專精於台灣股票市場的風險控管。
你的職責是評估個股持倉風險並提供清晰易懂的風險報告。
台股特點：每日漲跌限制±10%、T+2交割、集中市場流動性。
你的建議必須符合穩健的資金管理原則，保護本金是第一優先。"""

_TOOLS = [
    {
        "name": "generate_risk_report",
        "description": "生成持倉風險評估報告",
        "input_schema": {
            "type": "object",
            "properties": {
                "risk_summary": {
                    "type": "string",
                    "description": "風險摘要（1-2句話）"
                },
                "action_recommendation": {
                    "type": "string",
                    "enum": ["PROCEED", "REDUCE_SIZE", "AVOID"],
                    "description": "行動建議"
                },
                "adjusted_position_pct": {
                    "type": "number",
                    "description": "建議調整後的倉位百分比"
                },
                "key_risks": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "主要風險因素列表"
                },
                "stop_loss_advice": {
                    "type": "string",
                    "description": "停損建議說明"
                },
            },
            "required": ["risk_summary", "action_recommendation",
                         "adjusted_position_pct", "key_risks", "stop_loss_advice"],
        },
    }
]


class RiskAgent(BaseAgent):
    """Provides Claude-powered risk assessment with narrative explanations."""

    def __init__(self):
        super().__init__("RiskAgent", _SYSTEM)

    def assess(
        self,
        symbol: str,
        entry_price: float,
        df: pd.DataFrame,
        portfolio_value: float,
        existing_positions: int = 0,
        equity_curve: list[float] = None,
    ) -> dict:
        """
        Runs quantitative risk assessment then asks Claude for narrative evaluation.
        Returns combined dict with both quantitative metrics and narrative guidance.
        """
        # Quantitative assessment from risk manager
        quant = assess_position_risk(
            symbol, entry_price, df, portfolio_value, existing_positions
        )

        # Portfolio-level check
        portfolio_risk = check_portfolio_risk(equity_curve or [portfolio_value])

        prompt = self._build_prompt(quant, portfolio_risk, portfolio_value)
        response = self._call(
            prompt,
            tools=_TOOLS,
            tool_choice={"type": "tool", "name": "generate_risk_report"},
            max_tokens=2048,
        )
        narrative = self._extract_tool_input(response, "generate_risk_report")

        return {
            "symbol": quant.symbol,
            "position_size_pct": quant.position_size_pct,
            "suggested_stop_loss": quant.suggested_stop_loss,
            "suggested_take_profit": quant.suggested_take_profit,
            "risk_reward_ratio": quant.risk_reward_ratio,
            "risk_level": quant.risk_level,
            "quant_warnings": quant.warnings,
            "portfolio_drawdown_pct": portfolio_risk.get("drawdown_pct", 0),
            "portfolio_ok": portfolio_risk.get("ok", True),
            **narrative,
        }

    # ------------------------------------------------------------------ #
    def _build_prompt(
        self, quant: RiskAssessment, portfolio_risk: dict, portfolio_value: float
    ) -> str:
        lines = [
            f"## 個股風險評估：{quant.symbol}",
            f"- 建議倉位大小: {quant.position_size_pct:.1f}% (約 {portfolio_value * quant.position_size_pct / 100:,.0f} NTD)",
            f"- 建議停損價: {quant.suggested_stop_loss:.2f}",
            f"- 建議止盈價: {quant.suggested_take_profit:.2f}",
            f"- 風險報酬比: {quant.risk_reward_ratio:.2f}",
            f"- 風險等級: {quant.risk_level}",
        ]
        if quant.warnings:
            lines.append("- 警告:")
            for w in quant.warnings:
                lines.append(f"  * {w}")

        lines += [
            "",
            "## 投資組合層面",
            f"- 當前回撤: {portfolio_risk.get('drawdown_pct', 0):.2f}%",
            f"- 回撤限制: {portfolio_risk.get('limit_pct', 10):.0f}%",
            f"- 投資組合狀態: {'正常' if portfolio_risk.get('ok', True) else '⚠️ 超過回撤限制'}",
            "",
            "請根據以上量化數據，生成清晰的風險評估報告。",
            "如果投資組合已超過回撤限制，action_recommendation 應為 AVOID。",
            "呼叫 generate_risk_report 工具提交報告。",
        ]
        return "\n".join(lines)
