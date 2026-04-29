"""Persistent JSON storage for strategy parameters and performance history."""
import json
import os
from datetime import datetime
from typing import Any

from strategies.base_strategy import StrategyParams
from config import STORAGE_DIR, STRATEGY_STORE_FILE, PERFORMANCE_STORE_FILE, LEARNING_LOG_FILE


def _ensure_dir():
    os.makedirs(STORAGE_DIR, exist_ok=True)


def _load(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(path: str, data: dict):
    _ensure_dir()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── Strategy params ─────────────────────────────────────────────────────────

def load_strategy_params() -> dict[str, StrategyParams]:
    """Load all saved strategy params keyed by strategy name."""
    raw = _load(STRATEGY_STORE_FILE)
    return {name: StrategyParams.from_dict(d) for name, d in raw.items()}


def save_strategy_params(params_map: dict[str, StrategyParams]):
    data = {name: sp.to_dict() for name, sp in params_map.items()}
    _save(STRATEGY_STORE_FILE, data)


def update_strategy_param(strategy_name: str, new_params: dict, increment_version: bool = True):
    """Merge new_params into existing strategy params and optionally bump version."""
    current = load_strategy_params()
    sp = current.get(strategy_name, StrategyParams(name=strategy_name))
    sp.params.update(new_params)
    if increment_version:
        sp.version += 1
    current[strategy_name] = sp
    save_strategy_params(current)
    return sp


# ── Performance history ──────────────────────────────────────────────────────

def save_backtest_result(strategy_name: str, symbol: str, metrics_dict: dict, period: str):
    all_perf = _load(PERFORMANCE_STORE_FILE)
    key = f"{strategy_name}:{symbol}"
    if key not in all_perf:
        all_perf[key] = []
    all_perf[key].append({
        "timestamp": datetime.now().isoformat(),
        "period": period,
        "metrics": metrics_dict,
    })
    # Keep at most last 20 runs per strategy+symbol
    all_perf[key] = all_perf[key][-20:]
    _save(PERFORMANCE_STORE_FILE, all_perf)


def load_performance_history(strategy_name: str = None, symbol: str = None) -> dict:
    all_perf = _load(PERFORMANCE_STORE_FILE)
    if strategy_name and symbol:
        key = f"{strategy_name}:{symbol}"
        return {key: all_perf.get(key, [])}
    if strategy_name:
        return {k: v for k, v in all_perf.items() if k.startswith(strategy_name + ":")}
    return all_perf


# ── Learning log ─────────────────────────────────────────────────────────────

def append_learning_log(entry: dict):
    log = _load(LEARNING_LOG_FILE)
    entries: list = log.get("entries", [])
    entries.append({"timestamp": datetime.now().isoformat(), **entry})
    entries = entries[-50:]   # keep last 50 entries
    _save(LEARNING_LOG_FILE, {"entries": entries})


def load_learning_log() -> list[dict]:
    log = _load(LEARNING_LOG_FILE)
    return log.get("entries", [])
