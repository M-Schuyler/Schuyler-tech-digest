from __future__ import annotations

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
        draw.text((100, 260), "Today’s top three", font=subtitle_font, fill="#38bdf8")

        y = 330
        for idx, line in enumerate(brief.top_three[:3], start=1):
            draw.text((100, y), f"{idx}. {line}", font=bullet_font, fill="#e2e8f0")
            y += 135

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
