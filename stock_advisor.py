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
# 功能七：個股投資分析報告
# ──────────────────────────────────────────────

def fetch_advisor_report(symbol: str) -> dict:
    """取得個股完整投資分析資料（估值、技術、分析師）"""
    formatted = format_symbol(symbol)
    ticker = yf.Ticker(formatted)
    info = ticker.info
    fi = ticker.fast_info

    price = (fi.get("last_price") or info.get("currentPrice")
             or info.get("regularMarketPrice"))
    prev_close = fi.get("previous_close") or price
    change_pct = ((price - prev_close) / prev_close * 100) if (price and prev_close) else 0

    week52_high = info.get("fiftyTwoWeekHigh")
    week52_low  = info.get("fiftyTwoWeekLow")

    pe          = info.get("trailingPE")
    forward_pe  = info.get("forwardPE")
    pb          = info.get("priceToBook")
    eps         = info.get("trailingEps")
    eps_growth  = info.get("earningsGrowth")
    rev_growth  = info.get("revenueGrowth")
    beta        = info.get("beta")
    market_cap  = info.get("marketCap")

    # 殖利率：用 dividendRate / price 自行計算以避免 yfinance 欄位不一致
    div_rate    = info.get("dividendRate") or 0
    div_yield   = (div_rate / price) if (div_rate and price) else 0
    ex_div_ts   = info.get("exDividendDate")
    ex_div_date = (
        datetime.utcfromtimestamp(ex_div_ts).strftime("%Y-%m-%d")
        if ex_div_ts else "N/A"
    )

    # 分析師共識
    target_mean    = info.get("targetMeanPrice")
    target_high    = info.get("targetHighPrice")
    target_low     = info.get("targetLowPrice")
    recommendation = info.get("recommendationKey") or "N/A"
    num_analysts   = info.get("numberOfAnalystOpinions") or 0

    # 技術指標：MA20 / MA60 / RSI(14)，從 6 個月歷史資料計算
    hist = ticker.history(period="6mo")
    ma20 = ma60 = rsi = None
    if not hist.empty:
        closes = hist["Close"]
        if len(closes) >= 20:
            ma20 = float(closes.rolling(20).mean().iloc[-1])
        if len(closes) >= 60:
            ma60 = float(closes.rolling(60).mean().iloc[-1])
        if len(closes) >= 15:
            delta = closes.diff()
            gain  = delta.clip(lower=0).rolling(14).mean()
            loss  = (-delta.clip(upper=0)).rolling(14).mean()
            rs    = gain / loss
            rsi   = float((100 - 100 / (1 + rs)).iloc[-1])

    return {
        "symbol": formatted,
        "name": info.get("longName") or info.get("shortName", formatted),
        "currency": info.get("currency", "TWD"),
        "price": price, "change_pct": change_pct,
        "week52_high": week52_high, "week52_low": week52_low,
        "pe": pe, "forward_pe": forward_pe, "pb": pb,
        "eps": eps, "eps_growth": eps_growth, "rev_growth": rev_growth,
        "div_rate": div_rate, "div_yield": div_yield, "ex_div_date": ex_div_date,
        "beta": beta, "market_cap": market_cap,
        "target_mean": target_mean, "target_high": target_high, "target_low": target_low,
        "recommendation": recommendation, "num_analysts": num_analysts,
        "ma20": ma20, "ma60": ma60, "rsi": rsi,
    }


def _score_stock(d: dict) -> tuple:
    """
    基於量化指標計算投資評分（0–100）。
    起點 50（中性），各指標加減分。
    回傳 (score: int, comments: list[str])
    """
    score = 50
    comments = []

    price       = d.get("price")
    high52      = d.get("week52_high")
    low52       = d.get("week52_low")
    pe          = d.get("pe")
    forward_pe  = d.get("forward_pe")
    pb          = d.get("pb")
    div_yield   = d.get("div_yield", 0)
    target_mean = d.get("target_mean")
    rsi         = d.get("rsi")
    ma20        = d.get("ma20")
    ma60        = d.get("ma60")
    eps_growth  = d.get("eps_growth")
    rev_growth  = d.get("rev_growth")

    # ── 1. 股價在 52 週區間的位置 ──────────────────
    if price and high52 and low52 and (high52 > low52):
        pos = (price - low52) / (high52 - low52) * 100
        if pos < 25:
            score += 15
            comments.append(f"✅ 股價處於52週低檔 ({pos:.0f}%)，具安全邊際")
        elif pos < 50:
            score += 5
            comments.append(f"📊 股價處於52週中低檔 ({pos:.0f}%)")
        elif pos < 75:
            score -= 5
            comments.append(f"📊 股價處於52週中高檔 ({pos:.0f}%)")
        else:
            score -= 12
            comments.append(f"⚠️ 股價接近52週高點 ({pos:.0f}%)，須注意回檔風險")

    # ── 2. 本益比（半導體業參考值：合理 15–25x）──────
    if pe:
        if pe < 15:
            score += 15
            comments.append(f"✅ 本益比 {pe:.1f}x 偏低，具估值優勢")
        elif pe < 25:
            score += 5
            comments.append(f"📊 本益比 {pe:.1f}x 屬合理範圍")
        elif pe < 40:
            score -= 5
            comments.append(f"⚠️ 本益比 {pe:.1f}x 偏高，需成長性支撐")
        else:
            score -= 15
            comments.append(f"⛔ 本益比 {pe:.1f}x 過高，估值風險大")
    if forward_pe and pe and forward_pe < pe:
        diff = (pe - forward_pe) / pe * 100
        comments.append(f"✅ 遠期本益比 {forward_pe:.1f}x（低於TTM {diff:.0f}%），預期獲利改善")

    # ── 3. 股價淨值比 ────────────────────────────────
    if pb:
        if pb < 1.5:
            score += 10
            comments.append(f"✅ 股價淨值比 {pb:.2f}x，低於淨值的折價機會")
        elif pb < 3:
            score += 3
            comments.append(f"📊 股價淨值比 {pb:.2f}x，合理水準")
        elif pb < 6:
            comments.append(f"📊 股價淨值比 {pb:.2f}x，偏高但半導體業常見")
        else:
            score -= 8
            comments.append(f"⚠️ 股價淨值比 {pb:.2f}x，溢價較高")

    # ── 4. 殖利率 ─────────────────────────────────────
    if div_yield > 0:
        y = div_yield * 100
        if y >= 5:
            score += 10
            comments.append(f"✅ 殖利率 {y:.2f}%，高息適合存股")
        elif y >= 3:
            score += 5
            comments.append(f"📊 殖利率 {y:.2f}%，配息穩定")
        elif y >= 1:
            comments.append(f"📊 殖利率 {y:.2f}%，象徵性配息")
        else:
            comments.append(f"📊 殖利率極低，以資本利得為主要回報")
    else:
        comments.append("📊 目前無配息資料")

    # ── 5. 分析師目標價 ──────────────────────────────
    if target_mean and price and target_mean > 0:
        upside = (target_mean - price) / price * 100
        if upside >= 20:
            score += 15
            comments.append(f"✅ 分析師均價 {target_mean:.1f}，上漲空間 {upside:.1f}%")
        elif upside >= 5:
            score += 7
            comments.append(f"✅ 分析師均價 {target_mean:.1f}，上漲空間 {upside:.1f}%")
        elif upside >= -5:
            comments.append(f"📊 分析師均價 {target_mean:.1f}（{upside:+.1f}%），接近現價")
        else:
            score -= 10
            comments.append(f"⚠️ 分析師均價 {target_mean:.1f}（{upside:+.1f}%），有下行風險")

    # ── 6. RSI(14) 動量 ──────────────────────────────
    if rsi is not None:
        if rsi < 30:
            score += 12
            comments.append(f"✅ RSI {rsi:.1f}，技術超賣，短線反彈機率高")
        elif rsi < 45:
            score += 4
            comments.append(f"📊 RSI {rsi:.1f}，中性偏弱")
        elif rsi < 60:
            comments.append(f"📊 RSI {rsi:.1f}，正常區間")
        elif rsi < 75:
            score -= 5
            comments.append(f"⚠️ RSI {rsi:.1f}，偏強，短線注意過熱")
        else:
            score -= 12
            comments.append(f"⛔ RSI {rsi:.1f}，技術超買，短線回檔風險高")

    # ── 7. 均線排列 ──────────────────────────────────
    if ma20 is not None and price:
        if ma60 is not None:
            if price > ma20 > ma60:
                score += 5
                comments.append(f"✅ 多頭排列：現價 > MA20({ma20:.1f}) > MA60({ma60:.1f})")
            elif price < ma20 < ma60:
                score -= 5
                comments.append(f"⚠️ 空頭排列：現價 < MA20({ma20:.1f}) < MA60({ma60:.1f})")
            elif price > ma20:
                comments.append(f"📊 站上MA20({ma20:.1f})，短線偏多")
            else:
                comments.append(f"📊 跌破MA20({ma20:.1f})，短線偏弱")
        else:
            if price > ma20:
                score += 3
                comments.append(f"📊 現價 > MA20({ma20:.1f})，短線偏多")
            else:
                score -= 3
                comments.append(f"📊 現價 < MA20({ma20:.1f})，短線偏弱")

    # ── 8. EPS / 營收成長 ────────────────────────────
    if eps_growth is not None:
        g = eps_growth * 100
        if g >= 20:
            score += 8
            comments.append(f"✅ EPS年增率 {g:.1f}%，獲利快速成長")
        elif g >= 0:
            score += 2
            comments.append(f"📊 EPS年增率 {g:.1f}%，溫和成長")
        else:
            score -= 6
            comments.append(f"⚠️ EPS年增率 {g:.1f}%，獲利衰退中")
    if rev_growth is not None:
        g = rev_growth * 100
        if g >= 15:
            comments.append(f"✅ 營收年增率 {g:.1f}%，業績動能強勁")
        elif g >= 0:
            comments.append(f"📊 營收年增率 {g:.1f}%，穩健成長")
        else:
            comments.append(f"⚠️ 營收年增率 {g:.1f}%，營收下滑")

    score = max(0, min(100, score))
    return score, comments


def _rating_label(score: int) -> str:
    """將分數轉換為評級文字（含 ANSI 顏色）"""
    if score >= 75:
        return color("★★★★★  強力買進", "92")
    elif score >= 65:
        return color("★★★★☆  建議買進", "32")
    elif score >= 50:
        return color("★★★☆☆  中性持有", "33")
    elif score >= 35:
        return color("★★☆☆☆  建議觀望", "91")
    else:
        return color("★☆☆☆☆  不建議買入", "31")


def cmd_advisor_report() -> None:
    """互動：個股投資分析報告（量化評分）"""
    print(f"\n{DIVIDER}")
    print("【個股投資分析報告】")
    print("輸入股票代號，多支以空格或逗號分隔（台股輸數字，美股輸英文）")
    raw = input(">>> ").strip()
    if not raw:
        return

    symbols = parse_symbols(raw)
    for sym in symbols:
        print(f"\n⏳ 正在分析 {sym}，請稍候...")
        try:
            d = fetch_advisor_report(sym)
        except Exception as e:
            print(f"  資料取得失敗：{e}")
            continue

        score, comments = _score_stock(d)
        rating = _rating_label(score)

        price      = d.get("price")
        currency   = d.get("currency", "TWD")
        change     = d.get("change_pct", 0)
        pe         = d.get("pe")
        forward_pe = d.get("forward_pe")
        pb         = d.get("pb")
        eps        = d.get("eps")
        div_yield  = d.get("div_yield", 0)
        rsi        = d.get("rsi")
        ma20       = d.get("ma20")
        ma60       = d.get("ma60")
        target_mean= d.get("target_mean")
        target_high= d.get("target_high")
        target_low = d.get("target_low")
        rec        = d.get("recommendation", "N/A").upper()
        n_analysts = d.get("num_analysts", 0)
        high52     = d.get("week52_high")
        low52      = d.get("week52_low")
        beta       = d.get("beta")
        mktcap     = d.get("market_cap")
        eps_g      = d.get("eps_growth")

        print(f"\n{DIVIDER}")
        print(f"  {d['symbol']}  {d['name']}")
        if price:
            print(f"  現價：{price:,.2f} {currency}  {fmt_change(change)}")
        print(DIVIDER)

        # ── 基本估值表 ──────────────────────────────────
        rows = []
        rows.append(["本益比 (TTM)",   f"{pe:.1f}x"    if pe else "N/A",
                     "遠期本益比",      f"{forward_pe:.1f}x" if forward_pe else "N/A"])
        rows.append(["股價淨值比",      f"{pb:.2f}x"    if pb else "N/A",
                     "每股盈餘 EPS",   f"{eps:.2f}"    if eps else "N/A"])
        rows.append(["殖利率",          f"{div_yield*100:.2f}%" if div_yield else "N/A",
                     "EPS年增率",       f"{eps_g*100:.1f}%" if eps_g is not None else "N/A"])
        rows.append(["RSI (14)",        f"{rsi:.1f}"    if rsi else "N/A",
                     "Beta",            f"{beta:.2f}"   if beta else "N/A"])
        rows.append(["MA20",            f"{ma20:.1f}"   if ma20 else "N/A",
                     "MA60",            f"{ma60:.1f}"   if ma60 else "N/A"])
        if high52 and low52:
            rows.append(["52週高",      f"{high52:,.1f}",
                         "52週低",      f"{low52:,.1f}"])
        if target_mean:
            rows.append(["分析師均價",  f"{target_mean:.1f}",
                         "高/低目標",   f"{target_high:.1f} / {target_low:.1f}"
                                         if target_high and target_low else "N/A"])
        rows.append(["分析師評級",      rec,
                     "評級人數",        f"{n_analysts} 人"])
        if mktcap:
            rows.append(["市值",        f"{mktcap/1e8:,.0f} 億 {currency}", "", ""])

        print(tabulate(rows, tablefmt="simple", colalign=("left","right","left","right")))

        # ── 量化評語 ─────────────────────────────────────
        print(f"\n  ── 量化指標評語 ────────────────────────────")
        for c in comments:
            print(f"  {c}")

        # ── 綜合評分 ─────────────────────────────────────
        bar_filled = round(score / 5)
        bar = "█" * bar_filled + "░" * (20 - bar_filled)
        print(f"\n  ── 綜合評分 ─────────────────────────────────")
        print(f"  [{bar}] {score}/100")
        print(f"  評級：{rating}")
        print(f"\n  ⚠️  本報告僅供量化參考，不構成投資建議。")
        print(f"  ⚠️  投資前請結合產業動態、財報細節自行判斷。")
        print(DIVIDER)


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
║  7. 個股投資分析報告（量化評分）         ║
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
        elif choice == "7":
            cmd_advisor_report()
        elif choice == "0":
            print("再見！")
            break
        else:
            print("請輸入 0~6 的選項")


if __name__ == "__main__":
    main()
