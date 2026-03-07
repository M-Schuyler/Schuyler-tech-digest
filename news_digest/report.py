from __future__ import annotations

from datetime import date
from pathlib import Path

from .config import REPORT_DIR
from .db import StoredArticle


class MarkdownReportWriter:
    def __init__(self, output_dir: Path = REPORT_DIR) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def write(self, report_date: date, items: list[StoredArticle]) -> Path:
        report_path = self.output_dir / f"{report_date.isoformat()}.md"
        lines: list[str] = ["# 今日科技新闻", ""]

        if not items:
            lines.extend(["今日未抓取到可用新闻。", ""])
        else:
            for item in items:
                summary_lines = [line.strip() for line in item.summary.splitlines() if line.strip()]
                paired_lines: list[str] = []
                for idx in range(0, len(summary_lines), 2):
                    en = summary_lines[idx]
                    zh = summary_lines[idx + 1] if idx + 1 < len(summary_lines) else ""
                    paired_lines.append(f"- EN: {en}")
                    paired_lines.append(f"  ZH: {zh}")
                lines.extend(
                    [
                        f"## {item.title}",
                        f"来源：{item.source}",
                        "摘要：",
                        *paired_lines,
                        f"关键词：{item.keywords}",
                        f"链接：{item.url}",
                        "",
                    ]
                )

        report_path.write_text("\n".join(lines), encoding="utf-8")
        return report_path
