from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from ..config import ASSET_DIR, RuntimeSettings
from ..models import AlertEvent, CloseSummary


class AlertCardRenderer:
    def __init__(self, settings: RuntimeSettings) -> None:
        self.settings = settings

    def render_intraday(self, event: AlertEvent) -> Path:
        out_dir = ASSET_DIR / event.trading_date_ny.isoformat()
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"alert-{event.symbol.lower()}-{event.triggered_at_ny.strftime('%H%M')}.png"
        color = "#16a34a" if event.direction == "up" else "#dc2626"
        image = Image.new("RGB", (1080, 720), "#0b1220")
        draw = ImageDraw.Draw(image)
        title_font = _load_font(self.settings.font_path, 72)
        body_font = _load_font(self.settings.font_path, 34)
        draw.rounded_rectangle((50, 50, 1030, 670), radius=28, fill="#111827", outline=color, width=4)
        draw.text((100, 110), event.symbol, font=title_font, fill="#f8fafc")
        draw.text((100, 235), f"{event.magnitude_pct:+.2f}%  |  {event.kind.upper()}", font=body_font, fill=color)
        draw.text((100, 320), event.reason, font=body_font, fill="#cbd5e1")
        if event.related_symbols:
            draw.text((100, 400), "Related: " + " / ".join(event.related_symbols), font=body_font, fill="#94a3b8")
        image.save(out_path)
        return out_path

    def render_close(self, summary: CloseSummary) -> Path:
        out_dir = ASSET_DIR / summary.trade_date_ny.isoformat()
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "close-summary.png"
        image = Image.new("RGB", (1080, 720), "#0f172a")
        draw = ImageDraw.Draw(image)
        title_font = _load_font(self.settings.font_path, 60)
        body_font = _load_font(self.settings.font_path, 30)
        draw.rounded_rectangle((50, 50, 1030, 670), radius=28, fill="#111827", outline="#38bdf8", width=3)
        draw.text((100, 100), "Market Close", font=title_font, fill="#f8fafc")
        draw.text((100, 190), summary.trade_date_ny.isoformat(), font=body_font, fill="#94a3b8")
        draw.text((100, 270), summary.closing_verdict, font=body_font, fill="#e2e8f0")
        draw.text((100, 360), "Strongest: " + " / ".join(summary.strongest_assets[:3]), font=body_font, fill="#22c55e")
        draw.text((100, 420), "Weakest: " + " / ".join(summary.weakest_assets[:3]), font=body_font, fill="#ef4444")
        draw.text((100, 500), "Watch: " + " / ".join(item.symbol for item in summary.tomorrow_watch[:3]), font=body_font, fill="#cbd5e1")
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
