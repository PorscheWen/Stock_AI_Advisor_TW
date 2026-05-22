# AGENTS.md

## Cursor Cloud specific instructions

### Project overview

Single-file Python CLI application (`stock_advisor.py`) — a stock investment advisor for Taiwan (TWSE) and US markets. No web server, no database, no Docker.

### Prerequisites

- Python 3.10+ (uses `float | None` union syntax)
- Dependencies: `pip install -r requirements.txt` (installs `yfinance`, `tabulate`, `requests`)

### Running the app

```
python3 stock_advisor.py
```

The app is interactive (reads from stdin). When testing in automation, use a tmux session and `send-keys` to feed input, or pipe input via stdin.

### Lint / Test

- No linter or test framework is configured in this repo.
- Use `python3 -m py_compile stock_advisor.py` as a basic syntax check.

### Notes

- The app requires internet access to fetch stock data from Yahoo Finance via `yfinance`.
- Portfolio data is stored in a local `portfolio.json` file in the working directory.
- Stock prices may show as N/A when markets are closed; this is expected behavior from the Yahoo Finance API.
