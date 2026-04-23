from __future__ import annotations

import argparse
import logging
from datetime import date, datetime

from news_digest.pipeline import NewsPipeline
from news_digest.scheduling.jobs import run_close_alert, run_daily_brief, run_intraday_scan


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Tech + AI + market intelligence jobs")
    subparsers = parser.add_subparsers(dest="command")

    legacy = subparsers.add_parser("legacy-digest", help="Run the original tech-news digest pipeline")
    legacy.add_argument("--date", type=str, default=None, help="Report date in YYYY-MM-DD format")

    daily = subparsers.add_parser("daily-brief", help="Run the main AI + market daily brief")
    daily.add_argument("--date", type=str, default=None, help="Brief date in YYYY-MM-DD format")

    intraday = subparsers.add_parser("intraday-scan", help="Run one intraday market scan")
    intraday.add_argument(
        "--now",
        type=str,
        default=None,
        help="Override time in ISO-8601 format with timezone",
    )

    close = subparsers.add_parser("close-alert", help="Run the market close summary")
    close.add_argument(
        "--now",
        type=str,
        default=None,
        help="Override time in ISO-8601 format with timezone",
    )

    return parser.parse_args()


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def main() -> None:
    args = parse_args()
    setup_logging()

    command = args.command or "legacy-digest"
    if command == "legacy-digest":
        report_date = date.fromisoformat(args.date) if getattr(args, "date", None) else None
        pipeline = NewsPipeline()
        report_path, count = pipeline.run(report_date=report_date)
        print(f"Done. Articles processed: {count}. Report: {report_path}")
        return

    if command == "daily-brief":
        report_date = date.fromisoformat(args.date) if getattr(args, "date", None) else None
        brief = run_daily_brief(report_date_sh=report_date)
        print(f"Daily brief generated for {brief.brief_date_sh.isoformat()}")
        return

    if command == "intraday-scan":
        now = datetime.fromisoformat(args.now) if getattr(args, "now", None) else None
        result = run_intraday_scan(now=now)
        print(
            "Intraday scan finished. "
            f"evaluated={len(result.evaluated_symbols)} dispatched={len(result.dispatched_events)} "
            f"skipped_reason={result.skipped_reason}"
        )
        return

    if command == "close-alert":
        now = datetime.fromisoformat(args.now) if getattr(args, "now", None) else None
        summary = run_close_alert(now=now)
        if summary is None:
            print("Close alert skipped (outside close window).")
        else:
            print(f"Close summary generated for {summary.trade_date_ny.isoformat()}")
        return

    raise ValueError(f"Unsupported command: {command}")


if __name__ == "__main__":
    main()
