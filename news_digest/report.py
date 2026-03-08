from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .config import REPORT_DIR


@dataclass
class BriefingItem:
    title: str
    category: str
    summary_en: list[str]
    summary_zh: list[str]
    url: str
    importance_score: int


class MarkdownReportWriter:
    def __init__(self, output_dir: Path = REPORT_DIR, max_items: int = 10) -> None:
        self.output_dir = output_dir
        self.max_items = max_items
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def write(self, report_date: date, items: list[BriefingItem]) -> Path:
        report_path = self.output_dir / f"{report_date.isoformat()}.md"
        lines: list[str] = ["# Daily Tech Briefing", ""]

        selected = items[: self.max_items]
        if not selected:
            lines.extend(["No high-impact tech news selected today.", ""])
            report_path.write_text("\n".join(lines), encoding="utf-8")
            return report_path

        lines.extend([f"Date: {report_date.isoformat()}", f"Items: {len(selected)}", ""])

        for idx, item in enumerate(selected, start=1):
            lines.extend(
                [
                    f"## {idx}. {item.title}",
                    f"Category: {item.category}",
                    "EN Summary:",
                    f"1. {item.summary_en[0] if item.summary_en else ''}",
                    f"2. {item.summary_en[1] if len(item.summary_en) > 1 else ''}",
                    "中文摘要：",
                    f"1. {item.summary_zh[0] if item.summary_zh else ''}",
                    f"2. {item.summary_zh[1] if len(item.summary_zh) > 1 else ''}",
                    f"Link: {item.url}",
                    "",
                ]
            )

        report_path.write_text("\n".join(lines), encoding="utf-8")
        return report_path
