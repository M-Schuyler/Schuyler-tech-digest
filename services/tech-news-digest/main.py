from __future__ import annotations

import argparse
import logging
from datetime import date

from news_digest.pipeline import NewsPipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Tech news crawler and summarizer")
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Report date in YYYY-MM-DD format. Default: today",
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

    report_date = date.fromisoformat(args.date) if args.date else None

    pipeline = NewsPipeline()
    report_path, count = pipeline.run(report_date=report_date)
    print(f"Done. Articles processed: {count}. Report: {report_path}")


if __name__ == "__main__":
    main()
