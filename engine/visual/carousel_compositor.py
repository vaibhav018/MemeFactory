"""Compose carousel slides: rich background + bold text + pillar branding."""
from __future__ import annotations

import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter

_FONTS_DIR = Path(__file__).parent.parent.parent / "assets" / "fonts"

# Font candidates in priority order (what's actually in assets/fonts/)
_DISPLAY_FONTS = ["Anton-Regular.ttf", "Montserrat-ExtraBold.ttf", "BalooTammudu2-ExtraBold.ttf"]
_BODY_FONTS    = ["Montserrat-Regular.ttf", "NotoSans-Regular.ttf", "BalooTammudu2-Bold.ttf"]


def _load_font(candidates: list[str], size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in candidates:
        path = _FONTS_DIR / name
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size)
            except Exception:
                continue
    return ImageFont.load_default(size=size)


def _hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _wrap_text(text: str, font, max_width: int, draw: ImageDraw.ImageDraw) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        test = (current + " " + word).strip()
        w = draw.textlength(test, font=font)
        if w <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _draw_text_centered(
    draw: ImageDraw.ImageDraw,
    lines: list[str],
    font,
    canvas_w: int,
    y: int,
    color: tuple,
    line_gap: int = 14,
) -> int:
    """Draw lines centered horizontally. Returns y after last line."""
    for line in lines:
        w = draw.textlength(line, font=font)
        x = (canvas_w - w) // 2
        draw.text((x, y), line, font=font, fill=color)
        bbox = draw.textbbox((x, y), line, font=font)
        y += (bbox[3] - bbox[1]) + line_gap
    return y


def _darken(img: Image.Image, strength: int = 160) -> Image.Image:
    overlay = Image.new("RGBA", img.size, (0, 0, 0, strength))
    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")


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
    palette = pillar.get("visual_palette", {})
    accent = _hex_rgb(palette.get("accent", "#FFFFFF"))
    text_color = (255, 255, 255)
    dim_color  = (200, 200, 200)

    img = Image.open(bg_path).convert("RGB").resize((size, size), Image.LANCZOS)

    # Darker overlay on hook slide for maximum text contrast
    img = _darken(img, strength=175 if slide_num == 1 else 145)
    draw = ImageDraw.Draw(img)

    margin = 80
    content_w = size - 2 * margin

    # ── Slide counter pill (top-right) ──────────────────────────
    counter_font = _load_font(_BODY_FONTS, 30)
    counter_text = f"{slide_num} / {total_slides}"
    cw = draw.textlength(counter_text, font=counter_font)
    pill_x, pill_y = size - margin - int(cw) - 24, 44
    pill_w, pill_h = int(cw) + 24, 44
    draw.rounded_rectangle(
        [pill_x, pill_y, pill_x + pill_w, pill_y + pill_h],
        radius=22, fill=(*accent, 60)
    )
    draw.text((pill_x + 12, pill_y + 7), counter_text, font=counter_font, fill=text_color)

    # ── Pillar accent dot (top-left, replaces emoji which Anton can't render) ──
    dot_r = 18
    draw.ellipse([margin, 48, margin + dot_r * 2, 48 + dot_r * 2], fill=accent)

    # ── Main text ────────────────────────────────────────────────
    text = slide_data.get("text", "")
    is_hook = slide_num == 1
    is_cta  = slide_num == total_slides

    if is_hook:
        font = _load_font(_DISPLAY_FONTS, 88)
        lines = _wrap_text(text.upper(), font, content_w, draw)
        # vertical center
        total_h = sum(
            draw.textbbox((0, 0), l, font=font)[3] - draw.textbbox((0, 0), l, font=font)[1] + 18
            for l in lines
        )
        y = (size - total_h) // 2 - 40
        _draw_text_centered(draw, lines, font, size, y, text_color, line_gap=18)

        # Accent underline beneath hook text
        line_y = y + total_h + 24
        bar_w = int(size * 0.18)
        draw.rectangle(
            [(size // 2 - bar_w // 2, line_y), (size // 2 + bar_w // 2, line_y + 6)],
            fill=accent
        )

    elif is_cta:
        font = _load_font(_DISPLAY_FONTS, 66)
        lines = _wrap_text(text, font, content_w, draw)
        total_h = len(lines) * 80
        y = (size - total_h) // 2
        _draw_text_centered(draw, lines, font, size, y, text_color, line_gap=20)

    else:
        # Content slide — slide number as large background watermark
        num_font = _load_font(_DISPLAY_FONTS, 320)
        num_str = str(slide_num)
        nw = draw.textlength(num_str, font=num_font)
        # Draw large faint number
        draw.text(
            (size - int(nw) - 20, size - 340),
            num_str, font=num_font,
            fill=(*accent, 18)
        )

        body_font = _load_font(_BODY_FONTS, 56)
        lines = _wrap_text(text, body_font, content_w, draw)
        total_h = sum(
            draw.textbbox((0, 0), l, font=body_font)[3] - draw.textbbox((0, 0), l, font=body_font)[1] + 16
            for l in lines
        )
        y = (size - total_h) // 2
        _draw_text_centered(draw, lines, body_font, size, y, text_color, line_gap=16)

    # ── Left accent bar ──────────────────────────────────────────
    draw.rectangle([(0, 0), (6, size)], fill=accent)

    # ── Handle branding (bottom) ─────────────────────────────────
    handle_font = _load_font(_BODY_FONTS, 28)
    hw = draw.textlength(handle, font=handle_font)
    draw.text(((size - hw) // 2, size - 52), handle, font=handle_font, fill=(*dim_color, 200))

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
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    total = len(slides)
    for i, slide in enumerate(slides, start=1):
        out = output_dir / f"{post_id}_slide_{i:02d}.jpg"
        compose_slide(bg_path, slide, i, total, pillar, out, handle)
        paths.append(out)
        print(f"    slide {i}/{total} ✓")
    return paths
