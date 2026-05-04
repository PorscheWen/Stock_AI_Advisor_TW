#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
台股 / 美股智慧投資助理
功能：
  1. 即時股價查詢（台股 / 美股）
  2. 多股票同時查詢
  3. 配股配息資訊查詢
  4. 持股管理（成本、數量、獲利、年化報酬）

台股代號輸入純數字即可，例如 2330（台積電）、0050（元大台灣50）
美股輸入股票代號，例如 AAPL、TSLA、NVDA
"""

import json
import os
import sys
from datetime import datetime, date

try:
    import yfinance as yf
    from tabulate import tabulate
except ImportError:
    print("缺少必要套件，請先執行：pip install -r requirements.txt")
    sys.exit(1)

PORTFOLIO_FILE = "portfolio.json"
DIVIDER = "=" * 65


# ──────────────────────────────────────────────
# 工具函式
# ──────────────────────────────────────────────

def format_symbol(symbol: str) -> str:
    """
    將使用者輸入轉換為 yfinance 格式的代號。
    - 純數字 4 碼 → XXXX.TW（上市）
    - 純數字 5~6 碼或含字母（如 006208）→ 同樣嘗試 .TW
    - 美股：保持原始大寫
    """
    symbol = symbol.strip().upper()
    # 台股：全數字或以數字開頭且長度 ≤ 6
    if symbol.isdigit():
        return f"{symbol}.TW"
    return symbol


def load_portfolio() -> dict:
    """讀取持股組合 JSON 檔案"""
    if os.path.exists(PORTFOLIO_FILE):
        with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_portfolio(portfolio: dict) -> None:
    """儲存持股組合至 JSON 檔案"""
    with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
        json.dump(portfolio, f, ensure_ascii=False, indent=2)


def color(text: str, code: str) -> str:
    """ANSI 顏色輸出（正紅負綠）"""
    return f"\033[{code}m{text}\033[0m"


def fmt_change(value: float) -> str:
    """漲跌幅格式化，正紅負綠"""
    if value is None:
        return "N/A"
    sign = "▲" if value >= 0 else "▼"
    c = "91" if value >= 0 else "92"   # 紅/綠
    return color(f"{sign}{abs(value):.2f}%", c)


def fmt_profit(value: float) -> str:
    """獲利格式化，正紅負綠"""
    if value is None:
        return "N/A"
    c = "91" if value >= 0 else "92"
    return color(f"{value:+,.0f}", c)


def parse_symbols(raw: str) -> list:
    """解析使用者輸入的多個股票代號（空格或逗號分隔）"""
    return [s.strip() for s in raw.replace(",", " ").split() if s.strip()]


# ──────────────────────────────────────────────
# 功能一、二：即時股價查詢（支援多股票）
# ──────────────────────────────────────────────

def fetch_price_info(symbols: list) -> list:
    """
    批次取得股票即時資訊。
    回傳 list of dict，包含代號、名稱、現價、漲跌幅、成交量、幣別。
    """
    results = []
    for sym in symbols:
        formatted = format_symbol(sym)
        try:
            ticker = yf.Ticker(formatted)
            fi = ticker.fast_info          # 輕量快速資訊
            info = ticker.info            # 完整資訊（含名稱等）

            price = fi.get("last_price") or fi.get("previous_close")
            prev_close = fi.get("previous_close") or price
            change_pct = ((price - prev_close) / prev_close * 100) if prev_close else 0
            volume = fi.get("three_month_average_volume") or info.get("averageVolume")
            name = info.get("longName") or info.get("shortName") or formatted
            currency = info.get("currency", "---")

            results.append({
                "symbol": formatted,
                "original": sym.upper(),
                "name": name,
                "price": price,
                "change_pct": change_pct,
                "volume": volume,
                "currency": currency,
                "error": None,
            })
        except Exception as e:
            results.append({
                "symbol": formatted,
                "original": sym.upper(),
                "name": "查詢失敗",
                "price": None,
                "change_pct": None,
                "volume": None,
                "currency": "---",
                "error": str(e),
            })
    return results


def cmd_query_price() -> None:
    """互動：即時股價查詢"""
    print(f"\n{DIVIDER}")
    print("【即時股價查詢】")
    print("輸入股票代號，多支以空格或逗號分隔")
    print("台股輸入數字代號，美股輸入英文代號")
    raw = input(">>> ").strip()
    if not raw:
        return

    symbols = parse_symbols(raw)
    print(f"\n正在查詢 {len(symbols)} 支股票，請稍候...")
    results = fetch_price_info(symbols)

    rows = []
    for r in results:
        if r["error"]:
            rows.append([r["symbol"], r["name"], "N/A", "N/A", "N/A", r["currency"]])
        else:
            rows.append([
                r["symbol"],
                r["name"][:22],
                f"{r['price']:,.2f}" if r["price"] else "N/A",
                fmt_change(r["change_pct"]),
                f"{r['volume']:,.0f}" if r["volume"] else "N/A",
                r["currency"],
            ])

    headers = ["代號", "名稱", "現價", "漲跌幅", "均量", "幣別"]
    print(f"\n{tabulate(rows, headers=headers, tablefmt='grid')}")


# ──────────────────────────────────────────────
# 功能三：配股配息資訊查詢
# ──────────────────────────────────────────────

def fetch_dividend_info(symbol: str) -> dict:
    """取得單一股票的配股配息資訊"""
    formatted = format_symbol(symbol)
    ticker = yf.Ticker(formatted)
    info = ticker.info

    # 歷史股息
    dividends = ticker.dividends
    splits = ticker.splits

    # 除息日（Unix timestamp → 日期字串）
    ex_div_ts = info.get("exDividendDate")
    ex_div_date = (
        datetime.utcfromtimestamp(ex_div_ts).strftime("%Y-%m-%d")
        if ex_div_ts else "N/A"
    )

    # 近期配息紀錄（最近 8 筆）
    recent_div = []
    if not dividends.empty:
        for dt, amt in dividends.tail(8).items():
            recent_div.append((dt.strftime("%Y-%m-%d"), f"{amt:.4f}"))

    # 近期股票分割紀錄
    recent_splits = []
    if not splits.empty:
        for dt, ratio in splits.tail(5).items():
            recent_splits.append((dt.strftime("%Y-%m-%d"), f"{ratio:.2f}"))

    return {
        "symbol": formatted,
        "name": info.get("longName") or info.get("shortName", formatted),
        "currency": info.get("currency", "---"),
        "dividend_yield": info.get("dividendYield") or 0,
        "dividend_rate": info.get("dividendRate") or 0,
        "ex_dividend_date": ex_div_date,
        "payout_ratio": info.get("payoutRatio") or 0,
        "recent_dividends": recent_div,
        "recent_splits": recent_splits,
    }


def cmd_query_dividend() -> None:
    """互動：配股配息資訊查詢"""
    print(f"\n{DIVIDER}")
    print("【配股配息資訊查詢】")
    print("輸入股票代號，多支以空格或逗號分隔")
    raw = input(">>> ").strip()
    if not raw:
        return

    symbols = parse_symbols(raw)
    for sym in symbols:
        print(f"\n正在查詢 {sym} 的配息資訊，請稍候...")
        try:
            d = fetch_dividend_info(sym)
            print(f"\n{DIVIDER}")
            print(f"  {d['symbol']}  {d['name']}")
            print(DIVIDER)
            print(f"  殖利率：{d['dividend_yield']*100:.2f}%")
            print(f"  每股股息：{d['dividend_rate']:.4f} {d['currency']}")
            print(f"  配息率：{d['payout_ratio']*100:.1f}%")
            print(f"  最近除息日：{d['ex_dividend_date']}")

            if d["recent_dividends"]:
                print("\n  ── 近期配息紀錄 ──")
                print(tabulate(d["recent_dividends"],
                               headers=["除息日", f"每股股息({d['currency']})"],
                               tablefmt="simple"))
            else:
                print("\n  （無配息紀錄）")

            if d["recent_splits"]:
                print("\n  ── 近期股票分割 ──")
                print(tabulate(d["recent_splits"],
                               headers=["日期", "分割比例"],
                               tablefmt="simple"))
        except Exception as e:
            print(f"  查詢失敗：{e}")


# ──────────────────────────────────────────────
# 功能四：持股管理
# ──────────────────────────────────────────────

def cmd_add_holding(portfolio: dict) -> None:
    """互動：新增持股"""
    print(f"\n{DIVIDER}")
    print("【新增 / 加碼持股】")
    print("台股輸入數字代號，美股輸入英文代號")

    sym = input("股票代號 >>> ").strip()
    if not sym:
        return
    formatted = format_symbol(sym)

    try:
        shares = float(input("持有股數   >>> "))
        cost   = float(input("平均成本價 >>> "))
    except ValueError:
        print("輸入格式錯誤，請輸入數字")
        return

    buy_date_raw = input("買入日期 (YYYY-MM-DD，直接 Enter 為今日) >>> ").strip()
    buy_date = buy_date_raw if buy_date_raw else date.today().isoformat()

    # 驗證日期格式
    try:
        datetime.strptime(buy_date, "%Y-%m-%d")
    except ValueError:
        print("日期格式錯誤，已改用今日日期")
        buy_date = date.today().isoformat()

    if formatted not in portfolio:
        portfolio[formatted] = []

    portfolio[formatted].append({
        "shares": shares,
        "cost_per_share": cost,
        "buy_date": buy_date,
        "total_cost": round(shares * cost, 4),
    })

    save_portfolio(portfolio)
    print(f"\n✔ 已新增 {formatted}  {shares:.0f} 股  成本 {cost:.2f}  日期 {buy_date}")


def cmd_remove_holding(portfolio: dict) -> None:
    """互動：刪除持股"""
    if not portfolio:
        print("投資組合目前是空的。")
        return

    print(f"\n{DIVIDER}")
    print("【刪除持股】")
    print("目前持有：", ", ".join(portfolio.keys()))
    sym = input("請輸入要刪除的股票代號 >>> ").strip()
    if not sym:
        return
    formatted = format_symbol(sym)

    if formatted not in portfolio:
        print(f"找不到 {formatted}，請確認代號是否正確。")
        return

    holdings = portfolio[formatted]
    if len(holdings) > 1:
        print(f"\n{formatted} 有 {len(holdings)} 筆持倉：")
        for i, h in enumerate(holdings):
            print(f"  [{i}] 買入日：{h['buy_date']}  股數：{h['shares']}  成本：{h['cost_per_share']:.2f}")
        idx_raw = input("輸入要刪除的編號（直接 Enter 刪除全部）>>> ").strip()
        if idx_raw == "":
            del portfolio[formatted]
            print(f"已刪除 {formatted} 的全部持倉。")
        else:
            try:
                idx = int(idx_raw)
                portfolio[formatted].pop(idx)
                if not portfolio[formatted]:
                    del portfolio[formatted]
                print(f"已刪除第 {idx} 筆持倉。")
            except (ValueError, IndexError):
                print("無效的編號。")
    else:
        del portfolio[formatted]
        print(f"已刪除 {formatted} 的持倉。")

    save_portfolio(portfolio)


def _calc_annual_return(total_cost: float, current_value: float, buy_date: str) -> float | None:
    """計算年化報酬率（CAGR）"""
    try:
        buy_dt = datetime.strptime(buy_date, "%Y-%m-%d")
        years = (datetime.now() - buy_dt).days / 365.25
        if years < 0.01 or total_cost <= 0:
            return None
        return ((current_value / total_cost) ** (1 / years) - 1) * 100
    except Exception:
        return None


def cmd_view_portfolio(portfolio: dict) -> None:
    """互動：檢視持股損益明細"""
    if not portfolio:
        print("\n投資組合目前是空的，請先使用「新增持股」功能。")
        return

    symbols = list(portfolio.keys())
    print(f"\n正在查詢 {len(symbols)} 支持股的即時價格，請稍候...")
    price_map = {r["symbol"]: r for r in fetch_price_info(symbols)}

    rows = []
    grand_cost = 0.0
    grand_value = 0.0

    for symbol, holdings in portfolio.items():
        pinfo = price_map.get(symbol, {})
        current_price = pinfo.get("price")
        currency = pinfo.get("currency", "---")
        name = (pinfo.get("name") or symbol)[:16]

        for h in holdings:
            shares          = h["shares"]
            cost_per_share  = h["cost_per_share"]
            buy_date        = h["buy_date"]
            total_cost      = h["total_cost"]

            if current_price:
                current_value = shares * current_price
                profit        = current_value - total_cost
                profit_pct    = profit / total_cost * 100
                ann_ret       = _calc_annual_return(total_cost, current_value, buy_date)
                grand_cost  += total_cost
                grand_value += current_value
            else:
                current_value = profit = profit_pct = ann_ret = None

            rows.append([
                symbol,
                name,
                buy_date,
                f"{shares:,.0f}",
                f"{cost_per_share:.2f}",
                f"{current_price:,.2f}" if current_price else "N/A",
                f"{current_value:,.0f}" if current_value is not None else "N/A",
                fmt_profit(profit) if profit is not None else "N/A",
                fmt_change(profit_pct) if profit_pct is not None else "N/A",
                (f"{ann_ret:+.1f}%" if ann_ret is not None else "N/A"),
                currency,
            ])

    headers = ["代號", "名稱", "買入日", "股數", "成本價", "現價",
               "市值", "損益", "報酬%", "年化報酬%", "幣別"]
    print(f"\n{tabulate(rows, headers=headers, tablefmt='grid')}")

    # 摘要（僅統計成功取得價格者）
    if grand_cost > 0:
        grand_profit = grand_value - grand_cost
        grand_pct    = grand_profit / grand_cost * 100
        c = "91" if grand_profit >= 0 else "92"
        print(f"\n{'─'*65}")
        print(f"  總投入成本：{grand_cost:>14,.0f}")
        print(f"  現有市值　：{grand_value:>14,.0f}")
        print(f"  總損益　　：{color(f'{grand_profit:>+,.0f}', c):>14}")
        print(f"  整體報酬率：{color(f'{grand_pct:>+.1f}%', c)}")


def cmd_summary_by_stock(portfolio: dict) -> None:
    """互動：依股票彙總持股（合計多筆買入）"""
    if not portfolio:
        print("\n投資組合目前是空的。")
        return

    symbols = list(portfolio.keys())
    print(f"\n正在查詢即時價格，請稍候...")
    price_map = {r["symbol"]: r for r in fetch_price_info(symbols)}

    rows = []
    for symbol, holdings in portfolio.items():
        pinfo = price_map.get(symbol, {})
        current_price = pinfo.get("price")
        currency = pinfo.get("currency", "---")
        name = (pinfo.get("name") or symbol)[:16]

        total_shares = sum(h["shares"] for h in holdings)
        total_cost   = sum(h["total_cost"] for h in holdings)
        avg_cost     = total_cost / total_shares if total_shares else 0

        if current_price:
            current_value = total_shares * current_price
            profit        = current_value - total_cost
            profit_pct    = profit / total_cost * 100
        else:
            current_value = profit = profit_pct = None

        rows.append([
            symbol,
            name,
            f"{total_shares:,.0f}",
            f"{avg_cost:.2f}",
            f"{current_price:,.2f}" if current_price else "N/A",
            f"{current_value:,.0f}" if current_value is not None else "N/A",
            fmt_profit(profit) if profit is not None else "N/A",
            fmt_change(profit_pct) if profit_pct is not None else "N/A",
            currency,
        ])

    headers = ["代號", "名稱", "總股數", "平均成本", "現價", "市值", "損益", "報酬%", "幣別"]
    print(f"\n{tabulate(rows, headers=headers, tablefmt='grid')}")


# ──────────────────────────────────────────────
# 主選單
# ──────────────────────────────────────────────

MENU = """
╔══════════════════════════════════════════╗
║      台股 / 美股智慧投資助理             ║
╠══════════════════════════════════════════╣
║  1. 即時股價查詢（多股票同時查詢）       ║
║  2. 配股配息資訊查詢                     ║
║  3. 新增 / 加碼持股                      ║
║  4. 查看持股損益明細（每筆買入）         ║
║  5. 持股彙總（依股票合計）               ║
║  6. 刪除持股                             ║
║  0. 離開                                 ║
╚══════════════════════════════════════════╝
"""


def main() -> None:
    portfolio = load_portfolio()

    while True:
        print(MENU)
        choice = input("請選擇功能 >>> ").strip()

        if choice == "1":
            cmd_query_price()
        elif choice == "2":
            cmd_query_dividend()
        elif choice == "3":
            cmd_add_holding(portfolio)
        elif choice == "4":
            cmd_view_portfolio(portfolio)
        elif choice == "5":
            cmd_summary_by_stock(portfolio)
        elif choice == "6":
            cmd_remove_holding(portfolio)
        elif choice == "0":
            print("再見！")
            break
        else:
            print("請輸入 0~6 的選項")


if __name__ == "__main__":
    main()
