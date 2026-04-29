import os
from dotenv import load_dotenv

load_dotenv()

# API
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = "claude-opus-4-7"

# Taiwan stock market defaults
DEFAULT_SYMBOLS = [
    "2330.TW",  # TSMC
    "2317.TW",  # Hon Hai
    "2454.TW",  # MediaTek
    "2412.TW",  # Chunghwa Telecom
    "2308.TW",  # Delta Electronics
    "2382.TW",  # Quanta Computer
    "2303.TW",  # United Microelectronics
    "2881.TW",  # Fubon Financial
]

# Trading cost model (Taiwan stock market)
BUY_COMMISSION = 0.001425   # 0.1425%
SELL_COMMISSION = 0.001425  # 0.1425%
SELL_TAX = 0.003            # 0.3% transaction tax on sell
TOTAL_BUY_COST = BUY_COMMISSION
TOTAL_SELL_COST = SELL_COMMISSION + SELL_TAX

# Backtest defaults
BACKTEST_PERIOD = "1y"
INITIAL_CAPITAL = 1_000_000  # NTD

# Risk management
MAX_POSITION_PCT = 0.10     # 10% of portfolio per position
STOP_LOSS_PCT = 0.04        # 4% stop loss
TAKE_PROFIT_PCT = 0.10      # 10% take profit
MAX_DRAWDOWN_LIMIT = 0.10   # 10% max drawdown limit

# Storage
STORAGE_DIR = os.path.join(os.path.dirname(__file__), "storage", "data")
STRATEGY_STORE_FILE = os.path.join(STORAGE_DIR, "strategies.json")
PERFORMANCE_STORE_FILE = os.path.join(STORAGE_DIR, "performance.json")
LEARNING_LOG_FILE = os.path.join(STORAGE_DIR, "learning_log.json")
