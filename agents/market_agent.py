"""Market analysis agent — evaluates overall Taiwan market conditions."""
import json
from .base_agent import BaseAgent
from data.fetcher import fetch_stock_data
from data.indicators import add_all_indicators

_SYSTEM = """你是一位專業的台股市場分析師。你的任務是分析台灣股市的整體市場狀況，
包括趨勢、動能、波動度和市場情緒，並提供具體的交易環境評估。
請使用技術分析工具評估市場狀態，輸出 JSON 格式的分析結果。"""

_TOOLS = [
    {
        "name": "analyze_market_conditions",
        "description": "分析台股整體市場條件，評估當前市場趨勢和風險",
        "input_schema": {
            "type": "object",
            "properties": {
                "market_trend": {
                    "type": "string",
                    "enum": ["BULLISH", "BEARISH", "SIDEWAYS"],
                    "description": "整體市場趨勢"
                },
                "momentum_score": {
                    "type": "number",
                    "description": "市場動能分數，-100 到 100，正值表示上行動能"
                },
                "volatility_level": {
                    "type": "string",
                    "enum": ["LOW", "MEDIUM", "HIGH"],
                    "description": "市場波動程度"
                },
                "trading_environment": {
                    "type": "string",
                    "enum": ["FAVORABLE", "NEUTRAL", "UNFAVORABLE"],
                    "description": "當前交易環境評估"
                },
                "key_observations": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "關鍵市場觀察（最多5點）"
                },
                "recommended_position_scale": {
                    "type": "number",
                    "description": "建議倉位規模比例，0.0 到 1.0（1.0=正常倉位）"
                },
            },
            "required": [
                "market_trend", "momentum_score", "volatility_level",
                "trading_environment", "key_observations", "recommended_position_scale"
            ],
        },
    }
]


class MarketAgent(BaseAgent):
    """Analyzes Taiwan market conditions and recommends position scaling."""

    def __init__(self):
        super().__init__("MarketAgent", _SYSTEM)

    def analyze(self, index_symbol: str = "^TWII", symbols: list[str] = None) -> dict:
        """
        Fetches recent data for the market index and sample symbols,
        then asks Claude to evaluate current market conditions.
        Returns a dict matching the analyze_market_conditions schema.
        """
        market_summary = self._build_market_summary(index_symbol, symbols or [])
        prompt = f"""請分析以下台股市場數據，評估當前市場狀況：

{market_summary}

請呼叫 analyze_market_conditions 工具提供你的市場評估。"""

        response = self._call(
            prompt,
            tools=_TOOLS,
            tool_choice={"type": "tool", "name": "analyze_market_conditions"},
            max_tokens=2048,
        )
        result = self._extract_tool_input(response, "analyze_market_conditions")
        return result if result else self._default_conditions()

    # ------------------------------------------------------------------ #
    def _build_market_summary(self, index_symbol: str, symbols: list[str]) -> str:
        lines: list[str] = []

        # Taiwan index
        df_idx = fetch_stock_data(index_symbol, period="3mo")
        if df_idx is not None and len(df_idx) >= 20:
            df_idx = add_all_indicators(df_idx)
            last = df_idx.iloc[-1]
            prev = df_idx.iloc[-5]
            chg = (last["Close"] / prev["Close"] - 1) * 100
            lines.append(f"加權指數 ({index_symbol}): 收{last['Close']:.0f}, 5日漲幅{chg:+.2f}%")
            if "RSI" in df_idx.columns:
                lines.append(f"  RSI(14): {last['RSI']:.1f}")
            if "MACD" in df_idx.columns:
                lines.append(f"  MACD: {last['MACD']:.2f}, Signal: {last['MACD_Signal']:.2f}")
            if "BB_upper" in df_idx.columns:
                bb_pos = (last["Close"] - last["BB_lower"]) / (last["BB_upper"] - last["BB_lower"]) * 100
                lines.append(f"  布林帶位置: {bb_pos:.1f}%")
            if "ATR" in df_idx.columns:
                atr_pct = last["ATR"] / last["Close"] * 100
                lines.append(f"  ATR波動率: {atr_pct:.2f}%")

        # Sample individual stocks
        for sym in symbols[:3]:
            df = fetch_stock_data(sym, period="1mo")
            if df is None or len(df) < 10:
                continue
            df = add_all_indicators(df)
            last = df.iloc[-1]
            chg1d = (last["Close"] / df.iloc[-2]["Close"] - 1) * 100
            lines.append(f"{sym}: 收{last['Close']:.1f}, 日漲幅{chg1d:+.2f}%")

        return "\n".join(lines) if lines else "無法取得市場數據"

    @staticmethod
    def _default_conditions() -> dict:
        return {
            "market_trend": "SIDEWAYS",
            "momentum_score": 0,
            "volatility_level": "MEDIUM",
            "trading_environment": "NEUTRAL",
            "key_observations": ["無法取得市場分析"],
            "recommended_position_scale": 0.7,
        }
