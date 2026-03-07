from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import requests

from .config import REPORT_DIR
from .db import StoredArticle


THEME_RULES: list[tuple[str, list[str], str]] = [
    (
        "Regulation & Policy",
        ["government", "court", "tariff", "law", "regulation", "department", "policy"],
        "监管与政策",
    ),
    ("Security", ["security", "vulnerability", "cyber", "breach", "osha", "risk"], "安全与风险"),
    ("Hardware & Devices", ["chip", "hardware", "phone", "device", "switch", "nintendo", "gpu"], "硬件设备"),
    (
        "Business & Funding",
        ["fund", "startup", "invest", "acquisition", "valuation", "market", "revenue"],
        "商业与融资",
    ),
    ("Mobility & Energy", ["ev", "vehicle", "bike", "battery", "nuclear", "reactor", "rivian"], "出行与能源"),
    ("Platforms & Apps", ["x", "social", "app", "platform", "download", "users", "ads"], "平台与应用"),
    ("AI Models", ["ai", "model", "anthropic", "openai", "claude", "chatbot", "agent"], "AI 模型"),
]


@dataclass
class HighlightPoint:
    en: str
    zh: str
    theme_en: str
    theme_zh: str


class MarkdownReportWriter:
    def __init__(self, output_dir: Path = REPORT_DIR, max_highlights: int = 8) -> None:
        self.output_dir = output_dir
        self.max_highlights = max_highlights
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def write(self, report_date: date, items: list[StoredArticle]) -> Path:
        report_path = self.output_dir / f"{report_date.isoformat()}.md"
        lines: list[str] = ["# 今日科技圈新鲜事", ""]

        if not items:
            lines.extend(["今天没有抓到可用新闻。", ""])
            report_path.write_text("\n".join(lines), encoding="utf-8")
            return report_path

        points = _collect_points(items)
        focus = _build_focus_points(points, self.max_highlights)
        signal_en, signal_zh = _build_signals(points)

        lines.extend(["## Key Signals (EN)", "", f"- {signal_en}"])
        lines.extend(f"- [{point.theme_en}] {point.en}" for point in focus)
        lines.extend(["", "## 重点速览（中文）", "", f"- {signal_zh}"])
        lines.extend(f"- [{point.theme_zh}] {point.zh}" for point in focus)
        lines.append("")

        report_path.write_text("\n".join(lines), encoding="utf-8")
        return report_path


def _collect_points(items: list[StoredArticle]) -> list[HighlightPoint]:
    points: list[HighlightPoint] = []
    seen: set[str] = set()

    for item in items:
        en, zh = _extract_first_pair(item.summary)
        if not en:
            continue

        en = _build_compact_en(item.title, en)
        zh = _build_compact_zh(zh or "", en)
        key = re.sub(r"\W+", "", en.lower())
        if not key or key in seen:
            continue

        seen.add(key)
        theme_en, theme_zh = _detect_theme(en)
        points.append(HighlightPoint(en=en, zh=zh, theme_en=theme_en, theme_zh=theme_zh))

    return points


def _build_focus_points(points: list[HighlightPoint], limit: int) -> list[HighlightPoint]:
    grouped: dict[str, list[HighlightPoint]] = defaultdict(list)
    for point in points:
        grouped[point.theme_en].append(point)

    ordered_themes = sorted(
        grouped.keys(),
        key=lambda theme: (theme == "General Updates", -len(grouped[theme])),
    )
    selected: list[HighlightPoint] = []

    for theme in ordered_themes:
        selected.append(grouped[theme][0])
        if len(selected) >= limit:
            return selected

    if len(selected) < limit:
        used = {item.en for item in selected}
        for point in points:
            if point.en in used:
                continue
            selected.append(point)
            if len(selected) >= limit:
                break

    return selected


def _build_signals(points: list[HighlightPoint]) -> tuple[str, str]:
    if not points:
        return "No clear tech trend detected today.", "今天没有识别出明显的科技趋势。"

    grouped_count: dict[str, int] = defaultdict(int)
    theme_zh_map: dict[str, str] = {}
    for point in points:
        grouped_count[point.theme_en] += 1
        theme_zh_map[point.theme_en] = point.theme_zh

    ranked = sorted(
        grouped_count.items(),
        key=lambda item: (item[0] == "General Updates", -item[1]),
    )
    top = ranked[:3]
    en_themes = ", ".join(name for name, _ in top)
    zh_themes = "、".join(theme_zh_map[name] for name, _ in top)

    en_signal = f"Today's hottest directions are {en_themes}."
    zh_signal = f"今天最热方向集中在：{zh_themes}。"
    return en_signal, zh_signal


def _extract_first_pair(summary: str) -> tuple[str, str]:
    lines = [line.strip() for line in summary.splitlines() if line.strip()]
    if not lines:
        return "", ""

    if len(lines) == 1:
        return lines[0], ""

    return lines[0], lines[1]


def _detect_theme(sentence_en: str) -> tuple[str, str]:
    lower = sentence_en.lower()
    for theme_en, keywords, theme_zh in THEME_RULES:
        if any(_has_keyword(lower, keyword) for keyword in keywords):
            return theme_en, theme_zh
    return "General Updates", "综合动态"


def _has_keyword(text: str, keyword: str) -> bool:
    key = keyword.lower().strip()
    if not key:
        return False

    if re.fullmatch(r"[a-z0-9]+", key):
        return re.search(rf"\b{re.escape(key)}\b", text) is not None
    return key in text


def _build_compact_en(title: str, summary_en: str) -> str:
    title_clean = _clean_spaces(title).rstrip(".")
    word_count = len(title_clean.split())
    if 4 <= word_count <= 18:
        return title_clean
    return _compress_english(summary_en)


def _build_compact_zh(summary_zh: str, fallback_en: str) -> str:
    text = _clean_spaces(summary_zh)
    text = re.sub(r"^（中文翻译暂不可用，保留英文原文）", "", text)
    if not text or not _contains_cjk(text):
        translated = _translate_to_chinese(fallback_en)
        if translated:
            text = translated
        else:
            return fallback_en

    parts = re.split(r"[，；：]", text, maxsplit=1)
    candidate = parts[0].strip()
    candidate = re.sub(r"^(但是|而且|并且|另外|同时)", "", candidate).strip()
    if candidate and candidate[-1] not in "。！？":
        candidate += "。"
    return candidate


def _compress_english(text: str) -> str:
    clean = _clean_spaces(text)
    if not clean:
        return "No clear update."

    # Keep the main clause and drop trailing context clauses.
    candidate = re.split(r",\\s+(which|where|while|after|because|although)\\b", clean, maxsplit=1)[0]
    candidate = re.split(r"\\s+[-—]\\s+", candidate, maxsplit=1)[0]
    candidate = re.split(r";", candidate, maxsplit=1)[0]
    candidate = re.sub(r"^(But|And|So)\\s+", "", candidate, flags=re.IGNORECASE).strip(" ,")

    if candidate and candidate[-1] not in ".!?":
        candidate += "."
    return candidate


def _clean_spaces(text: str) -> str:
    return re.sub(r"\\s+", " ", text).strip()


def _contains_cjk(text: str) -> bool:
    return re.search(r"[\u4e00-\u9fff]", text) is not None


def _translate_to_chinese(text: str) -> str:
    clean = _clean_spaces(text)
    if not clean:
        return ""

    try:
        response = requests.get(
            "https://translate.googleapis.com/translate_a/single",
            params={
                "client": "gtx",
                "sl": "auto",
                "tl": "zh-CN",
                "dt": "t",
                "q": clean,
            },
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
        chunks = data[0] if isinstance(data, list) and data else []
        return "".join(chunk[0] for chunk in chunks if isinstance(chunk, list) and chunk).strip()
    except requests.RequestException:
        return ""
