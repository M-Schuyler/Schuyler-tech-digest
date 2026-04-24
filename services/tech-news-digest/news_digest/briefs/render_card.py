from __future__ import annotations

import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from ..config import ASSET_DIR, RuntimeSettings
from ..models import DailyBrief


class DailyBriefCardRenderer:
    def __init__(self, settings: RuntimeSettings) -> None:
        self.settings = settings

    def render(self, brief: DailyBrief) -> Path:
        out_dir = ASSET_DIR / brief.brief_date_sh.isoformat()
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "brief-card.png"

        image = Image.new("RGB", (1200, 900), "#0f172a")
        draw = ImageDraw.Draw(image)
        title_font = _load_font(self.settings.font_path, 54)
        subtitle_font = _load_font(self.settings.font_path, 26)
        bullet_font = _load_font(self.settings.font_path, 34)

        draw.rectangle((0, 0, 1200, 900), fill="#111827")
        draw.rounded_rectangle((60, 60, 1140, 840), radius=36, fill="#111827", outline="#334155", width=2)
        draw.text((100, 105), "AI + Market Brief", font=title_font, fill="#f8fafc")
        draw.text(
            (100, 180),
            f"{brief.brief_date_sh.isoformat()}  |  Reference close: {brief.reference_trade_date_ny.isoformat()}",
            font=subtitle_font,
            fill="#94a3b8",
        )
        draw.text((100, 260), "Today's top three", font=subtitle_font, fill="#38bdf8")

        y = 320
        max_text_width = 1000
        line_height = _line_height(bullet_font)
        for idx, line in enumerate(brief.top_three[:3], start=1):
            wrapped_lines = _wrap_text_to_width(draw, f"{idx}. {line}", font=bullet_font, max_width=max_text_width)
            for wrapped_line in _limit_lines(draw, wrapped_lines, font=bullet_font, max_width=max_text_width, max_lines=2):
                draw.text((100, y), wrapped_line, font=bullet_font, fill="#e2e8f0")
                y += line_height
            y += 24

        draw.text((100, 760), "Watchlist: " + " / ".join(item.symbol for item in brief.watchlist[:3]), font=subtitle_font, fill="#cbd5e1")
        image.save(out_path)
        return out_path


def _load_font(preferred_path: str, size: int):
    candidates = [
        preferred_path,
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            try:
                return ImageFont.truetype(candidate, size=size)
            except OSError:
                continue
    return ImageFont.load_default()


_TEXT_TOKEN_RE = re.compile(r"\s+|[A-Za-z0-9][A-Za-z0-9_./:+%$#@&+=-]*|.")


def _wrap_text_to_width(
    draw: ImageDraw.ImageDraw,
    text: str,
    *,
    font: ImageFont.ImageFont,
    max_width: int,
) -> list[str]:
    lines: list[str] = []
    current = ""

    for raw_token in _TEXT_TOKEN_RE.findall(text.strip()):
        token = " " if raw_token.isspace() else raw_token
        if token == " " and not current:
            continue

        candidate = current + token
        if draw.textlength(candidate, font=font) <= max_width:
            current = candidate
            continue

        if current:
            lines.append(current.rstrip())
            current = ""

        if token == " ":
            continue

        token = token.lstrip()
        if draw.textlength(token, font=font) <= max_width:
            current = token
            continue

        for char in token:
            candidate = current + char
            if current and draw.textlength(candidate, font=font) > max_width:
                lines.append(current)
                current = char
            else:
                current = candidate

    if current.strip():
        lines.append(current.rstrip())

    return lines or [""]


def _limit_lines(
    draw: ImageDraw.ImageDraw,
    lines: list[str],
    *,
    font: ImageFont.ImageFont,
    max_width: int,
    max_lines: int,
) -> list[str]:
    if len(lines) <= max_lines:
        return lines

    limited = lines[:max_lines]
    limited[-1] = _fit_suffix(draw, limited[-1], font=font, max_width=max_width, suffix="...")
    return limited


def _fit_suffix(
    draw: ImageDraw.ImageDraw,
    text: str,
    *,
    font: ImageFont.ImageFont,
    max_width: int,
    suffix: str,
) -> str:
    text = text.rstrip()
    while text and draw.textlength(text + suffix, font=font) > max_width:
        text = text[:-1].rstrip()
    return text + suffix


def _line_height(font: ImageFont.ImageFont) -> int:
    bbox = font.getbbox("AI主线")
    return max(42, bbox[3] - bbox[1] + 14)
