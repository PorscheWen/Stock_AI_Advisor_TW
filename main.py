"""Entry point for the Taiwan Stock AI Advisor."""
import argparse
import sys
from rich.console import Console

console = Console()


def parse_args():
    parser = argparse.ArgumentParser(
        description="台股 AI 策略顧問 — 高獲利低風險自主學習系統",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  python main.py                          # 全流程（回測+學習）
  python main.py --symbols 2330.TW 2317.TW  # 指定標的
  python main.py --no-learning            # 只回測，不學習
  python main.py --backtest-only          # 同上
  python main.py --learning-only          # 只運行學習循環
  python main.py --show-log               # 顯示學習歷史
        """,
    )
    parser.add_argument(
        "--symbols", nargs="+", default=None,
        help="台股代碼（如 2330.TW 2317.TW），預設使用 config.py 中的 DEFAULT_SYMBOLS"
    )
    parser.add_argument(
        "--capital", type=float, default=None,
        help="初始資本（NTD），預設使用 config.py 中的 INITIAL_CAPITAL"
    )
    parser.add_argument(
        "--no-learning", action="store_true",
        help="跳過學習循環，只執行回測"
    )
    parser.add_argument(
        "--backtest-only", action="store_true",
        help="等同於 --no-learning"
    )
    parser.add_argument(
        "--learning-only", action="store_true",
        help="只運行學習循環（使用已有的回測歷史）"
    )
    parser.add_argument(
        "--show-log", action="store_true",
        help="顯示學習歷史紀錄並退出"
    )
    return parser.parse_args()


def show_learning_log():
    from storage.store import load_learning_log
    from rich.panel import Panel
    logs = load_learning_log()
    if not logs:
        console.print("[yellow]尚無學習記錄。請先執行至少一次完整分析。[/yellow]")
        return
    console.print(Panel(f"[bold]學習歷史 ({len(logs)} 筆記錄)[/bold]", expand=False))
    for i, entry in enumerate(logs, 1):
        ts = entry.get("timestamp", "")[:16]
        summary = entry.get("analysis_summary", "")[:100]
        applied = entry.get("applied_updates", [])
        console.print(f"\n[cyan]#{i}[/cyan] [{ts}]")
        console.print(f"  {summary}")
        if applied:
            console.print(f"  已更新策略: {[u['strategy'] for u in applied]}")
        for insight in entry.get("insights", [])[:2]:
            console.print(f"  • {insight}")


def run_learning_only():
    from agents.learning_agent import LearningAgent
    console.print("[bold yellow]運行學習循環...[/bold yellow]")
    agent = LearningAgent()
    result = agent.run_learning_cycle()
    if result.get("status") == "ok":
        console.print(f"\n[green]學習完成[/green]")
        console.print(result.get("analysis_summary", ""))
        for upd in result.get("applied_updates", []):
            console.print(f"  ✓ {upd['strategy']} → {upd['updates']}")
        console.print(f"\n下次重點：{result.get('next_focus', '')}")
    else:
        console.print(f"[red]學習失敗：{result.get('reason', '')}[/red]")


def main():
    args = parse_args()

    if args.show_log:
        show_learning_log()
        return

    if args.learning_only:
        run_learning_only()
        return

    # Full cycle or backtest-only
    from agents.orchestrator import Orchestrator
    from config import INITIAL_CAPITAL

    capital = args.capital or INITIAL_CAPITAL
    run_learning = not (args.no_learning or args.backtest_only)

    orchestrator = Orchestrator(
        symbols=args.symbols,
        portfolio_value=capital,
    )
    orchestrator.run_full_cycle(run_learning=run_learning)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]已中止[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]錯誤：{e}[/red]")
        raise
