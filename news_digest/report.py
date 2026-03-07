from __future__ import annotations

from datetime import date
from pathlib import Path

from .config import REPORT_DIR
from .db import StoredArticle


class MarkdownReportWriter:
    def __init__(self, output_dir: Path = REPORT_DIR, max_highlights: int = 10) -> None:
        self.output_dir = output_dir
        self.max_highlights = max_highlights
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def write(self, report_date: date, items: list[StoredArticle]) -> Path:
        report_path = self.output_dir / f"{report_date.isoformat()}.md"
        lines: list[str] = ["# 今日科技圈新鲜事", ""]

        if not items:
            lines.extend(["今日未抓取到可用新闻。", ""])
        else:
            highlights_en, highlights_zh = _collect_highlights(items, self.max_highlights)
            lines.extend(["## English Highlights", ""])
            lines.extend(f"- {point}" for point in highlights_en)
            lines.extend(["", "## 中文热点", ""])
            lines.extend(f"- {point}" for point in highlights_zh)
            lines.append("")

        report_path.write_text("\n".join(lines), encoding="utf-8")
        return report_path


def _collect_highlights(items: list[StoredArticle], max_highlights: int) -> tuple[list[str], list[str]]:
    highlights_en: list[str] = []
    highlights_zh: list[str] = []
    seen: set[str] = set()

    for item in items:
        en, zh = _extract_first_pair(item.summary)
        if not en:
            continue

        key = en.lower()
        if key in seen:
            continue
        seen.add(key)
        highlights_en.append(en)
        highlights_zh.append(zh or en)

        if len(highlights_en) >= max_highlights:
            break

    if not highlights_en:
        return ["No major tech updates available today."], ["今天暂无可用的科技热点更新。"]

    return highlights_en, highlights_zh


def _extract_first_pair(summary: str) -> tuple[str, str]:
    lines = [line.strip() for line in summary.splitlines() if line.strip()]
    if not lines:
        return "", ""

    if len(lines) == 1:
        return lines[0], ""

    return lines[0], lines[1]
