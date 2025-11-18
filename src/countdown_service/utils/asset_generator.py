"""Utilities for generating countdown assets."""
from __future__ import annotations

import io
from datetime import timedelta
from typing import Literal

from PIL import Image, ImageDraw, ImageFont

from .time_utils import humanize_delta

CANVAS_SIZE = (600, 200)
BACKGROUND_COLORS = {
    "digital": (15, 15, 40),
    "minimal": (245, 245, 245),
}
FOREGROUND_COLORS = {
    "digital": (0, 255, 180),
    "minimal": (33, 33, 33),
}


def _load_font(size: int = 48) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype("DejaVuSansMono.ttf", size)
    except Exception:
        return ImageFont.load_default()


def generate_asset(delta: timedelta, style: Literal["digital", "minimal"], fmt: str) -> bytes:
    """Render a countdown asset as a PNG or GIF and return the bytes."""

    bg = BACKGROUND_COLORS.get(style, BACKGROUND_COLORS["digital"])
    fg = FOREGROUND_COLORS.get(style, FOREGROUND_COLORS["digital"])
    image = Image.new("RGB", CANVAS_SIZE, color=bg)
    draw = ImageDraw.Draw(image)
    font = _load_font(64 if style == "digital" else 48)
    text = humanize_delta(delta)
    text_width, text_height = draw.textsize(text, font=font)
    position = ((CANVAS_SIZE[0] - text_width) / 2, (CANVAS_SIZE[1] - text_height) / 2)
    draw.text(position, text, fill=fg, font=font)

    buffer = io.BytesIO()
    save_format = "GIF" if fmt.lower() == "gif" else "PNG"
    image.save(buffer, format=save_format)
    return buffer.getvalue()
