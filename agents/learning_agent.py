"""
Learning agent — the self-improvement core.

Reads performance history across all strategies, identifies patterns,
and autonomously updates strategy parameters to improve future returns.
"""
import json
from .base_agent import BaseAgent
from storage.store import (
    load_performance_history, load_strategy_params,
    update_strategy_param, append_learning_log, load_learning_log,
)

_SYSTEM = """你是一個自主學習的量化交易AI。你的使命是持續分析策略績效，
識別改善機會，並自主更新策略參數以追求更高報酬與更低風險。

你的工作流程：
1. 分析各策略的歷史績效趨勢
2. 識別表現最差的指標（例如：Sharpe低、勝率差、回撤大）
3. 根據技術分析原理提出有針對性的參數調整
4. 記錄學習心得供未來參考

重要原則：
- 每次調整保守漸進（單一參數變動不超過20%）
- 避免過度擬合：如果交易次數太少，先增加訊號敏感度
- 優先改善風險指標（Sharpe、回撤）而非單純追求報酬
- 記錄每次學習的推理過程"""

_TOOLS = [
    {
        "name": "learning_decision",
        "description": "記錄學習決策：分析結果、參數更新計畫和學習心得",
        "input_schema": {
            "type": "object",
            "properties": {
                "analysis_summary": {
                    "type": "string",
                    "description": "整體績效分析摘要"
                },
                "strategy_updates": {
                    "type": "array",
                    "description": "各策略的參數更新列表",
                    "items": {
                        "type": "object",
                        "properties": {
                            "strategy_name": {"type": "string"},
                            "parameter_updates": {"type": "object"},
                            "reason": {"type": "string"},
                            "priority": {
                                "type": "string",
                                "enum": ["HIGH", "MEDIUM", "LOW"]
                            },
                        },
                        "required": ["strategy_name", "parameter_updates",
                                     "reason", "priority"],
                    },
                },
                "learning_insights": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "本次學習的重要發現（供未來參考）"
                },
                "next_focus": {
                    "type": "string",
                    "description": "下次學習循環應重點關注的方向"
                },
            },
            "required": ["analysis_summary", "strategy_updates",
                         "learning_insights", "next_focus"],
        },
    }
]


class LearningAgent(BaseAgent):
    """
    Self-learning agent that autonomously refines strategy parameters
    based on accumulated performance history.
    """

    def __init__(self):
        super().__init__("LearningAgent", _SYSTEM)

    def run_learning_cycle(self) -> dict:
        """
        Full learning cycle:
        1. Load all performance history
        2. Load current strategy params
        3. Load recent learning log for context
        4. Ask Claude to analyze and propose updates
        5. Apply approved updates (HIGH/MEDIUM priority)
        6. Log the learning session

        Returns: summary of what was learned and changed.
        """
        perf_history = load_performance_history()
        current_params = load_strategy_params()
        recent_logs = load_learning_log()[-5:]  # last 5 learning sessions

        if not perf_history:
            return {"status": "skipped", "reason": "無回測歷史，請先運行回測"}

        prompt = self._build_prompt(perf_history, current_params, recent_logs)
        response = self._call(
            prompt,
            tools=_TOOLS,
            tool_choice={"type": "tool", "name": "learning_decision"},
            max_tokens=8192,
        )
        decision = self._extract_tool_input(response, "learning_decision")
        if not decision:
            return {"status": "error", "reason": "無法解析學習決策"}

        # Apply parameter updates
        applied = []
        skipped = []
        for update in decision.get("strategy_updates", []):
            strategy_name = update.get("strategy_name", "")
            param_updates = update.get("parameter_updates", {})
            priority = update.get("priority", "LOW")

            if not param_updates:
                continue

            if priority in ("HIGH", "MEDIUM"):
                sp = update_strategy_param(strategy_name, param_updates, increment_version=True)
                applied.append({
                    "strategy": strategy_name,
                    "updates": param_updates,
                    "new_version": sp.version,
                    "reason": update.get("reason", ""),
                })
            else:
                skipped.append({
                    "strategy": strategy_name,
                    "updates": param_updates,
                    "reason": f"Priority={priority}, 暫緩執行",
                })

        # Log this learning session
        log_entry = {
            "analysis_summary": decision.get("analysis_summary", ""),
            "applied_updates": applied,
            "skipped_updates": skipped,
            "insights": decision.get("learning_insights", []),
            "next_focus": decision.get("next_focus", ""),
        }
        append_learning_log(log_entry)

        return {
            "status": "ok",
            "analysis_summary": decision.get("analysis_summary", ""),
            "applied_updates": applied,
            "skipped_updates": skipped,
            "insights": decision.get("learning_insights", []),
            "next_focus": decision.get("next_focus", ""),
        }

    # ------------------------------------------------------------------ #
    def _build_prompt(
        self,
        perf_history: dict,
        current_params: dict,
        recent_logs: list[dict],
    ) -> str:
        lines = ["# 自主學習分析任務", ""]

        # Performance history section
        lines.append("## 各策略回測績效歷史")
        for key, runs in perf_history.items():
            if not runs:
                continue
            lines.append(f"\n### {key}")
            for run in runs[-4:]:  # last 4 runs
                m = run.get("metrics", {})
                lines.append(
                    f"  [{run.get('timestamp', '')[:16]}] "
                    f"報酬: {m.get('total_return_pct', 0):+.2f}%, "
                    f"Sharpe: {m.get('sharpe_ratio', 0):.3f}, "
                    f"回撤: {m.get('max_drawdown_pct', 0):.2f}%, "
                    f"勝率: {m.get('win_rate_pct', 0):.1f}%, "
                    f"交易次數: {m.get('num_trades', 0)}"
                )

        # Current parameters section
        lines.append("\n## 當前策略參數")
        for name, sp in current_params.items():
            lines.append(f"\n### {name} (版本 {sp.version})")
            lines.append(json.dumps(sp.params, ensure_ascii=False, indent=2))

        # Previous learning insights
        if recent_logs:
            lines.append("\n## 近期學習記錄（供參考）")
            for log in recent_logs[-3:]:
                lines.append(f"- {log.get('analysis_summary', '')[:100]}")
                for insight in log.get("insights", [])[:2]:
                    lines.append(f"  * {insight[:80]}")

        lines += [
            "",
            "## 你的任務",
            "1. 識別每個策略表現最差的指標",
            "2. 分析是否有改善趨勢（對比多次回測）",
            "3. 為每個策略提出具體的參數調整（HIGH=立即執行，MEDIUM=本次執行，LOW=觀察）",
            "4. 記錄關鍵學習心得",
            "",
            "呼叫 learning_decision 工具提交你的分析和決策。",
        ]
        return "\n".join(lines)
