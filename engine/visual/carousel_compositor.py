"""Compose carousel slides: background + text overlay + branding.

Each slide = background image + semi-transparent text panel + pillar emoji
+ slide counter (e.g. "2 / 7") + account handle at bottom.

Returns list of saved image paths.
"""
from __future__ import annotations

import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

_FONTS_DIR = Path(__file__).parent.parent.parent / "assets" / "fonts"

# Font preference order — first one found is used
_BOLD_FONTS = [
    "Montserrat-ExtraBold.ttf",
    "Montserrat-Bold.ttf",
    "NotoSans-Bold.ttf",
    "DejaVuSans-Bold.ttf",
]
_REGULAR_FONTS = [
    "Montserrat-Regular.ttf",
    "NotoSans-Regular.ttf",
    "DejaVuSans.ttf",
]


def _find_font(names: list[str], size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in names:
        path = _FONTS_DIR / name
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def _draw_text_block(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    x: int,
    y: int,
    max_width: int,
    fill: tuple[int, int, int, int] = (255, 255, 255, 255),
    line_spacing: int = 12,
) -> int:
    """Draw wrapped text, return y position after last line."""
    avg_char_w = font.getlength("A") if hasattr(font, "getlength") else 20
    chars_per_line = max(1, int(max_width / avg_char_w))
    lines = textwrap.wrap(text, width=chars_per_line)
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        bbox = draw.textbbox((x, y), line, font=font)
        y += (bbox[3] - bbox[1]) + line_spacing
    return y


def _darken_bg(img: Image.Image, alpha: int = 140) -> Image.Image:
    overlay = Image.new("RGBA", img.size, (0, 0, 0, alpha))
    base = img.convert("RGBA")
    return Image.alpha_composite(base, overlay).convert("RGB")


def compose_slide(
    bg_path: Path,
    slide_data: dict,
    slide_num: int,
    total_slides: int,
    pillar: dict,
    output_path: Path,
    handle: str = "@modernmastery",
    size: int = 1080,
) -> Path:
    """Render one slide and save it. Returns output_path."""
    palette = pillar.get("visual_palette", {})
    accent_hex = palette.get("accent", "#FFFFFF")
    accent_rgb = tuple(int(accent_hex.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))

    img = Image.open(bg_path).convert("RGB").resize((size, size), Image.LANCZOS)
    img = _darken_bg(img, alpha=150 if slide_num == 1 else 120)

    draw = ImageDraw.Draw(img)
    margin = 72
    content_w = size - 2 * margin

    # fonts
    hook_font = _find_font(_BOLD_FONTS, 68 if slide_num == 1 else 56)
    body_font = _find_font(_REGULAR_FONTS, 46)
    small_font = _find_font(_REGULAR_FONTS, 28)
    emoji_font = _find_font(_BOLD_FONTS, 80)

    # Slide counter (top right)
    counter_text = f"{slide_num} / {total_slides}"
    draw.text((size - margin - 120, 40), counter_text, font=small_font, fill=(200, 200, 200, 255))

    # Emoji (top left)
    emoji = slide_data.get("emoji", pillar.get("emoji", ""))
    if emoji:
        draw.text((margin, 36), emoji, font=emoji_font, fill=(255, 255, 255, 255))

    # Main text
    text = slide_data.get("text", "")
    font = hook_font if slide_num in (1, 7) else body_font

    if slide_num == 1:
        # Centered vertically for hook slide
        y_start = size // 2 - 160
    else:
        y_start = 160

    _draw_text_block(draw, text, font, margin, y_start, content_w, fill=(255, 255, 255, 255))

    # Accent line under hook
    if slide_num == 1:
        draw.rectangle([margin, size - 160, size - margin, size - 156], fill=accent_rgb + (255,))  # type: ignore[operator]

    # Handle / branding (bottom)
    draw.text((margin, size - 56), handle, font=small_font, fill=(180, 180, 180, 200))

    img.save(output_path, format="JPEG", quality=92)
    return output_path


def compose_carousel(
    bg_path: Path,
    slides: list[dict],
    pillar: dict,
    output_dir: Path,
    post_id: str,
    handle: str = "@modernmastery",
) -> list[Path]:
    """Compose all slides, return list of image paths."""
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    total = len(slides)
    for i, slide in enumerate(slides, start=1):
        out = output_dir / f"{post_id}_slide_{i:02d}.jpg"
        compose_slide(bg_path, slide, i, total, pillar, out, handle)
        paths.append(out)
    return paths
