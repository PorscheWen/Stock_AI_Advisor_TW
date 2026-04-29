"""Abstract base class for all trading strategies."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Optional
import pandas as pd


@dataclass
class Signal:
    date: str
    symbol: str
    action: str          # "BUY" | "SELL" | "HOLD"
    price: float
    stop_loss: float
    take_profit: float
    confidence: float    # 0.0 – 1.0
    reason: str


@dataclass
class StrategyParams:
    name: str
    version: int = 1
    params: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "StrategyParams":
        return cls(name=d["name"], version=d.get("version", 1), params=d.get("params", {}))


class BaseStrategy(ABC):
    """All concrete strategies must inherit from this."""

    def __init__(self, params: Optional[StrategyParams] = None):
        self.params = params or StrategyParams(name=self.name)

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def default_params(self) -> dict:
        ...

    def get_param(self, key: str):
        return self.params.params.get(key, self.default_params.get(key))

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame, symbol: str) -> list[Signal]:
        """Return a list of signals for the given price data with indicators."""
        ...

    def __repr__(self):
        return f"{self.name}(v{self.params.version})"
