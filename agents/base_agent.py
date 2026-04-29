"""Base Claude agent with prompt caching and adaptive thinking."""
import anthropic
from typing import Any
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL


class BaseAgent:
    """
    Thin wrapper around the Anthropic API.
    - Uses claude-opus-4-7 with adaptive thinking
    - Caches the system prompt (prompt caching)
    - Provides tool_use helpers
    """

    def __init__(self, name: str, system_prompt: str):
        self.name = name
        self._system_prompt = system_prompt
        self._client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    def _call(
        self,
        user_message: str,
        tools: list[dict] = None,
        tool_choice: dict = None,
        max_tokens: int = 4096,
    ) -> anthropic.types.Message:
        """Single Claude call with prompt caching on system prompt."""
        kwargs: dict[str, Any] = {
            "model": CLAUDE_MODEL,
            "max_tokens": max_tokens,
            "thinking": {"type": "adaptive"},
            "system": [
                {
                    "type": "text",
                    "text": self._system_prompt,
                    "cache_control": {"type": "ephemeral"},  # cache system prompt
                }
            ],
            "messages": [{"role": "user", "content": user_message}],
        }
        if tools:
            kwargs["tools"] = tools
        if tool_choice:
            kwargs["tool_choice"] = tool_choice

        return self._client.messages.create(**kwargs)

    def _extract_text(self, response: anthropic.types.Message) -> str:
        """Extract the first text block from a response."""
        for block in response.content:
            if block.type == "text":
                return block.text
        return ""

    def _extract_tool_input(self, response: anthropic.types.Message, tool_name: str) -> dict:
        """Extract tool call input from a response."""
        for block in response.content:
            if block.type == "tool_use" and block.name == tool_name:
                return block.input
        return {}
