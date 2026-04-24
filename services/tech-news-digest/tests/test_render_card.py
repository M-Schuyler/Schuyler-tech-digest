from __future__ import annotations

from PIL import Image, ImageDraw

from news_digest.briefs.render_card import _load_font, _wrap_text_to_width


def test_wrap_text_to_width_splits_mixed_language_lines_by_pixel_width() -> None:
    image = Image.new("RGB", (1200, 900))
    draw = ImageDraw.Draw(image)
    font = _load_font("", 34)
    text = (
        "AI基础设施进入成本战：OpenAI local gateway, Gemini fallback, "
        "NVIDIA/AMD and market signals all point to a longer mixed-cycle risk"
    )

    lines = _wrap_text_to_width(draw, text, font=font, max_width=620)

    assert len(lines) > 1
    assert "".join(line.replace(" ", "") for line in lines) == text.replace(" ", "")
    assert all(draw.textlength(line, font=font) <= 620 for line in lines)
