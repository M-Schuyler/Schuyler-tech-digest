from __future__ import annotations

from collections import Counter
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
        lines: list[str] = ["# 今日科技快报（中文一眼版）", ""]

        selected = items[: self.max_items]
        if not selected:
            lines.extend(["今天暂无符合筛选条件的高价值科技新闻。", ""])
            report_path.write_text("\n".join(lines), encoding="utf-8")
            return report_path

        lines.extend([f"日期：{report_date.isoformat()}", f"入选新闻：{len(selected)} 条", ""])
        lines.extend(["## 一眼看懂", ""])
        lines.append(f"- 热门方向：{_category_overview(selected)}")
        lines.append(f"- 今日结论：{_overall_takeaway(selected)}")
        lines.append(f"- 最高热度：{max(item.importance_score for item in selected)} / 100")
        lines.append("")

        lines.extend(["## 最值得关注（Top 3）", ""])
        for idx, item in enumerate(selected[:3], start=1):
            lines.append(f"- 重点{idx}（{_category_zh(item.category)}）：{_focus_sentence(item)}")
        lines.append("")

        startup_signals = [_focus_sentence(item) for item in selected if item.category == "Startups"][:2]
        if startup_signals:
            lines.extend(["## 融资与公司动作", ""])
            for signal in startup_signals:
                lines.append(f"- {signal}")
            lines.append("")

        chips_robotics = [
            _focus_sentence(item)
            for item in selected
            if item.category in {"Chips", "Robotics"}
        ][:2]
        if chips_robotics:
            lines.extend(["## 产业与技术突破", ""])
            for signal in chips_robotics:
                lines.append(f"- {signal}")
            lines.append("")

        report_path.write_text("\n".join(lines), encoding="utf-8")
        return report_path


def _category_overview(items: list[BriefingItem]) -> str:
    counts = Counter(item.category for item in items)
    if not counts:
        return "暂无显著主题"

    ordered = sorted(counts.items(), key=lambda x: (-x[1], x[0]))
    return "、".join(f"{_category_zh(name)} {count}条" for name, count in ordered[:3])


def _overall_takeaway(items: list[BriefingItem]) -> str:
    counts = Counter(item.category for item in items)
    parts: list[str] = []
    takeaway_map = {
        "AI": "AI 进展密集，模型与应用同步推进",
        "Big Tech": "科技大厂动作频繁，生态变化值得跟踪",
        "Chips": "芯片与算力供应链持续升温",
        "Startups": "投融资保持活跃，创业赛道继续分化",
        "Robotics": "机器人与自动化落地继续提速",
    }

    ordered = sorted(counts.items(), key=lambda x: (-x[1], x[0]))
    for category, _ in ordered[:2]:
        phrase = takeaway_map.get(category)
        if phrase:
            parts.append(phrase)

    if not parts:
        return "今天以常规更新为主，暂无明显单一主线。"

    return "；".join(parts) + "。"


def _focus_sentence(item: BriefingItem) -> str:
    primary = (item.summary_zh[0] if item.summary_zh else "").strip()
    secondary = (item.summary_zh[1] if len(item.summary_zh) > 1 else "").strip()

    if primary and secondary and secondary != primary:
        sentence = f"{primary} {secondary}"
    else:
        sentence = primary or secondary or "该新闻暂无可用中文摘要。"

    return sentence


def _category_zh(name: str) -> str:
    mapping = {
        "AI": "人工智能",
        "Robotics": "机器人",
        "Chips": "芯片",
        "Big Tech": "科技大厂",
        "Startups": "创业融资",
    }
    return mapping.get(name, name)
