#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
依 portfolio.json 抓取公開報價，試算：
  1) 52 週區間「下 30% 帶」相對便宜判斷
  2) 成熟股本益比帶：EPS×10～EPS×12（僅當 trailing PE 落在約 5～40 且 EPS>0）

資料來源：yfinance（延遲／錯誤可能；台股請再以券商為準）。
用法：
  python valuation_bands.py
  python valuation_bands.py --md > valuation_snapshot.md
"""

from __future__ import annotations

import argparse
import json
import os
import sys

try:
    import yfinance as yf
except ImportError:
    print("請先安裝：pip install yfinance", file=sys.stderr)
    sys.exit(1)

PORTFOLIO_FILE = "portfolio.json"


def cheap_upper_52w(lo: float | None, hi: float | None, frac: float = 0.30) -> float | None:
    if lo is None or hi is None or hi <= lo:
        return None
    return lo + frac * (hi - lo)


def main() -> None:
    parser = argparse.ArgumentParser(description="Portfolio valuation bands helper")
    parser.add_argument("--md", action="store_true", help="輸出 Markdown 表格")
    args = parser.parse_args()

    path = os.path.join(os.path.dirname(__file__) or ".", PORTFOLIO_FILE)
    if not os.path.exists(path):
        print(f"找不到 {path}", file=sys.stderr)
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        portfolio = json.load(f)

    symbols = list(portfolio.keys())
    rows = []

    for sym in symbols:
        t = yf.Ticker(sym)
        info = t.info or {}
        try:
            fi = t.fast_info
        except Exception:
            fi = {}

        price = fi.get("last_price") or info.get("currentPrice") or info.get("regularMarketPrice")
        lo = info.get("fiftyTwoWeekLow")
        hi = info.get("fiftyTwoWeekHigh")
        eps = info.get("trailingEps")
        pe = info.get("trailingPE")
        name = (info.get("shortName") or info.get("longName") or sym).replace("|", "/")

        pct_range = None
        if price is not None and lo is not None and hi is not None and hi > lo:
            pct_range = (price - lo) / (hi - lo) * 100.0

        cu = cheap_upper_52w(lo, hi, 0.30)
        in_cheap_52w = (price is not None and cu is not None and price <= cu)

        use_pe_band = bool(eps and eps > 0 and pe and 5 <= pe <= 40)
        p10 = eps * 10 if use_pe_band else None
        p12 = eps * 12 if use_pe_band else None

        rows.append(
            {
                "sym": sym.replace(".TW", ""),
                "name": name[:24],
                "price": price,
                "lo": lo,
                "hi": hi,
                "pct_range": pct_range,
                "cheap_cut": cu,
                "cheap52": in_cheap_52w,
                "eps": eps,
                "pe": pe,
                "p10": p10,
                "p12": p12,
            }
        )

    if args.md:
        print("### 試算快照（公開資料，延遲／錯誤可能）\n")
        print("| 代號 | 名稱 | 參考現價 | 52週低～高 | 區間位置 | 下30%上緣 | 相對便宜? | PE | EPS×10～×12 |")
        print("|------|------|----------|------------|----------|-----------|-----------|-----|-------------|")
        for r in rows:
            week = "—"
            if r["lo"] is not None and r["hi"] is not None:
                week = f"{r['lo']:,.2f}～{r['hi']:,.2f}"
            pos = f"{r['pct_range']:.1f}%" if r["pct_range"] is not None else "—"
            cu = f"{r['cheap_cut']:,.2f}" if r["cheap_cut"] is not None else "—"
            ch = "是" if r["cheap52"] else "否"
            pe_s = f"{r['pe']:.2f}" if r["pe"] is not None else "—"
            band = "—"
            if r["p10"] is not None and r["p12"] is not None:
                band = f"{r['p10']:,.2f}～{r['p12']:,.2f}"
            px = f"{r['price']:,.2f}" if r["price"] is not None else "—"
            print(
                f"| {r['sym']} | {r['name']} | {px} | {week} | {pos} | {cu} | {ch} | {pe_s} | {band} |"
            )
        print("\n*相對便宜：現價 ≤ 52週低點 + (高−低)×30%。EPS×10～12 僅在 PE 約 5～40 時啟用。*\n")
    else:
        for r in rows:
            print(
                f"{r['sym']}\t{r['name']}\tprice={r['price']}\t52w={r['lo']}~{r['hi']}\t"
                f"pct={r['pct_range']}\tcheap30={r['cheap_cut']}\tcheap52={r['cheap52']}\t"
                f"PE={r['pe']}\tband10-12={r['p10']}~{r['p12']}"
            )


if __name__ == "__main__":
    main()
