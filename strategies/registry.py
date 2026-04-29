"""Strategy registry – maps names to classes and manages active strategy params."""
from .base_strategy import BaseStrategy, StrategyParams
from .kd_strategy import KDStrategy
from .rsi_strategy import RSIStrategy
from .macd_strategy import MACDStrategy

_REGISTRY: dict[str, type[BaseStrategy]] = {
    "KD_Strategy": KDStrategy,
    "RSI_Strategy": RSIStrategy,
    "MACD_Strategy": MACDStrategy,
}


def get_all_strategies(strategy_params: dict[str, StrategyParams] = None) -> list[BaseStrategy]:
    """Instantiate all registered strategies, injecting custom params where provided."""
    strategies = []
    for name, cls in _REGISTRY.items():
        sp = (strategy_params or {}).get(name)
        strategies.append(cls(params=sp))
    return strategies


def get_strategy(name: str, params: StrategyParams = None) -> BaseStrategy:
    cls = _REGISTRY.get(name)
    if cls is None:
        raise ValueError(f"Unknown strategy: {name}. Available: {list(_REGISTRY)}")
    return cls(params=params)


def list_strategy_names() -> list[str]:
    return list(_REGISTRY.keys())
