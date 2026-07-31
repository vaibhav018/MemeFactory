"""Modern color-blocked carousel compositor — 1080×1350 portrait format.

Layout per slide:
  ┌─────────────────────────────────┐
  │  ACCENT HEADER BLOCK (220px)    │  ← pillar name + slide counter
  ├─────────────────────────────────┤
  │                                 │
  │   DARK CONTENT ZONE (~940px)    │  ← big faint number + centered text
  │                                 │
  ├─────────────────────────────────┤
  │  DARK FOOTER STRIP (190px)      │  ← handle + swipe hint
  └─────────────────────────────────┘

Hook slide flips: full dark bg, massive text, accent bottom block.
CTA slide: accent top, dark bottom with CTA text.
"""
from __future__ import annotations

import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter

_FONTS_DIR = Path(__file__).parent.parent.parent / "assets" / "fonts"
_W, _H = 1080, 1350          # portrait — 20% more screen on mobile
_HEADER_H = 220
_FOOTER_H = 130
_CONTENT_H = _H - _HEADER_H - _FOOTER_H   # ~1000px

_DISPLAY = ["Anton-Regular.ttf", "Montserrat-ExtraBold.ttf", "BalooTammudu2-ExtraBold.ttf"]
_BODY    = ["Montserrat-Regular.ttf", "NotoSans-Regular.ttf", "BalooTammudu2-Bold.ttf"]


def _font(candidates: list[str], size: int):
    for name in candidates:
        p = _FONTS_DIR / name
        if p.exists():
            try:
                return ImageFont.truetype(str(p), size)
            except Exception:
                continue
    return ImageFont.load_default(size=size)


def _hex(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _wrap(text: str, font, max_w: int, draw: ImageDraw.ImageDraw) -> list[str]:
    words = text.split()
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if draw.textlength(test, font=font) <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _draw_centered(draw, lines, font, canvas_w, y, color, gap=16) -> int:
    for line in lines:
        lw = draw.textlength(line, font=font)
        x = (canvas_w - lw) // 2
        draw.text((x, y), line, font=font, fill=color)
        bb = draw.textbbox((x, y), line, font=font)
        y += (bb[3] - bb[1]) + gap
    return y


def _bg(path: Path) -> Image.Image:
    return Image.open(path).convert("RGB").resize((_W, _H), Image.LANCZOS)


# ── individual slide composers ──────────────────────────────────────────────

def _slide_hook(bg: Image.Image, text: str, pillar: dict, num: int, total: int,
                handle: str) -> Image.Image:
    """Slide 1: curiosity-first — category pill, massive hook, teaser line, progress dots."""
    palette = pillar["visual_palette"]
    acc = _hex(palette["accent"])
    dark = _hex(palette["primary"])

    img = Image.new("RGB", (_W, _H), dark)
    blurred = bg.filter(ImageFilter.GaussianBlur(30))
    overlay = Image.new("RGBA", (_W, _H), (*dark, 205))
    img = Image.alpha_composite(blurred.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)
    margin = 80
    content_w = _W - 2 * margin

    # ── Category pill (top center) ────────────────────────────────
    pill_font = _font(_BODY, 30)
    pill_text = "  " + pillar["emoji"] + "  " + pillar["name"].upper() + "  "
    pw = int(draw.textlength(pill_text, font=pill_font))
    pill_x = (_W - pw) // 2
    pill_y = 90
    pill_h = 54
    draw.rounded_rectangle([pill_x - 4, pill_y, pill_x + pw + 4, pill_y + pill_h],
                           radius=27, fill=(*acc, 220))
    draw.text((pill_x, pill_y + 12), pill_text, font=pill_font, fill=(255, 255, 255))

    # ── Hook text — massive uppercase ─────────────────────────────
    hook_font = _font(_DISPLAY, 100)
    lines = _wrap(text.upper(), hook_font, content_w, draw)
    line_h = 110
    total_text_h = len(lines) * line_h
    y_hook = max(pill_y + pill_h + 90, (_H - total_text_h) // 2 - 100)
    y_after = _draw_centered(draw, lines, hook_font, _W, y_hook, (255, 255, 255), gap=14)

    # ── Accent underline ──────────────────────────────────────────
    line_y = y_after + 32
    bar_w = int(_W * 0.20)
    bar_x = (_W - bar_w) // 2
    draw.rectangle([(bar_x, line_y), (bar_x + bar_w, line_y + 7)], fill=acc)

    # ── Teaser line ───────────────────────────────────────────────
    teaser_font = _font(_BODY, 34)
    teaser = str(total - 1) + " facts inside  →"
    tw = draw.textlength(teaser, font=teaser_font)
    draw.text(((_W - tw) // 2, line_y + 40), teaser, font=teaser_font, fill=(*acc, 230))

    # ── Progress dots ─────────────────────────────────────────────
    dot_y = _H - 190
    dot_r = 10
    dot_gap = 32
    total_dot_w = total * dot_gap
    dot_x_start = (_W - total_dot_w) // 2
    for i in range(total):
        cx = dot_x_start + i * dot_gap + dot_r
        if i == 0:
            draw.ellipse([cx - dot_r, dot_y - dot_r, cx + dot_r, dot_y + dot_r], fill=acc)
        else:
            draw.ellipse([cx - dot_r + 3, dot_y - dot_r + 3,
                         cx + dot_r - 3, dot_y + dot_r - 3], fill=(255, 255, 255, 55))

    # ── Handle ────────────────────────────────────────────────────
    handle_font = _font(_BODY, 28)
    hw = draw.textlength(handle, font=handle_font)
    draw.text(((_W - hw) // 2, _H - 120), handle, font=handle_font, fill=(180, 180, 180))

    # ── Left accent bar ───────────────────────────────────────────
    draw.rectangle([(0, 0), (7, _H)], fill=acc)

    return img


def _slide_content(bg: Image.Image, text: str, slide_num: int, total: int,
                   pillar: dict, handle: str) -> Image.Image:
    """Slides 2-6: color header block + dark content + footer."""
    palette = pillar["visual_palette"]
    acc = _hex(palette["accent"])
    dark = _hex(palette["primary"])
    grad = _hex(palette["gradient_to"])

    img = Image.new("RGB", (_W, _H), dark)
    blurred = bg.filter(ImageFilter.GaussianBlur(22))
    overlay = Image.new("RGBA", (_W, _H), (*dark, 195))
    img = Image.alpha_composite(blurred.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    margin = 80
    content_w = _W - 2 * margin

    # ── HEADER BLOCK ──────────────────────────────────────────────
    draw.rectangle([(0, 0), (_W, _HEADER_H)], fill=acc)

    # Pillar name in header
    label_font = _font(_DISPLAY, 36)
    label = pillar["name"].upper()
    lw = draw.textlength(label, font=label_font)
    draw.text(((_W - lw) // 2, 42), label, font=label_font,
              fill=(255, 255, 255))

    # Slide counter pill in header (right side)
    count_font = _font(_BODY, 28)
    count_txt = f"{slide_num} / {total}"
    ctw = draw.textlength(count_txt, font=count_font)
    pill_x = _W - margin - int(ctw) - 20
    pill_y = _HEADER_H - 68
    draw.rounded_rectangle([pill_x, pill_y, pill_x + int(ctw) + 20, pill_y + 48],
                           radius=24, fill=(0, 0, 0, 90))
    draw.text((pill_x + 10, pill_y + 10), count_txt, font=count_font,
              fill=(255, 255, 255))

    # Thin white separator under header
    draw.rectangle([( 0, _HEADER_H), (_W, _HEADER_H + 4)],
                   fill=(255, 255, 255, 40))

    # ── LARGE FAINT NUMBER (design element) ────────────────────────
    num_font = _font(_DISPLAY, 380)
    num_str = str(slide_num)
    nw = draw.textlength(num_str, font=num_font)
    draw.text((_W - int(nw) - 10, _H - _FOOTER_H - 360),
              num_str, font=num_font, fill=(*acc, 22))

    # ── CONTENT TEXT ───────────────────────────────────────────────
    body_font = _font(_BODY, 58)
    lines = _wrap(text, body_font, content_w, draw)
    line_h = 58 + 18
    total_text_h = len(lines) * line_h
    content_mid = _HEADER_H + (_H - _HEADER_H - _FOOTER_H) // 2
    y = content_mid - total_text_h // 2
    _draw_centered(draw, lines, body_font, _W, y, (255, 255, 255), gap=18)

    # Left accent bar (content zone only)
    draw.rectangle([(0, _HEADER_H + 4), (7, _H - _FOOTER_H)], fill=acc)

    # ── FOOTER ─────────────────────────────────────────────────────
    draw.rectangle([(0, _H - _FOOTER_H), (_W, _H)], fill=(*grad, 255))
    handle_font = _font(_BODY, 26)
    hw = draw.textlength(handle, font=handle_font)
    draw.text(((_W - hw) // 2, _H - _FOOTER_H + 38), handle,
              font=handle_font, fill=(200, 200, 200))

    # Swipe hint on non-last slide
    if slide_num < total - 1:
        hint_font = _font(_BODY, 22)
        hint = "swipe →"
        hiw = draw.textlength(hint, font=hint_font)
        draw.text((_W - margin - int(hiw), _H - _FOOTER_H + 40), hint,
                  font=hint_font, fill=(*acc, 180))

    return img


def _slide_split(bg: Image.Image, slide_data: dict, slide_num: int, total: int,
                 pillar: dict, handle: str) -> Image.Image:
    """Content slide, split-screen comparison layout (Free|Paid, Myth|Reality, etc.).

    Expects slide_data with: left_label, left_text, right_label, right_text.
    Left column uses white bg + dark text; right column uses accent bg + white text —
    high-contrast side-by-side that reads as "vs" at a glance while thumb-scrolling.
    """
    palette = pillar["visual_palette"]
    acc = _hex(palette["accent"])
    dark = _hex(palette["primary"])
    grad = _hex(palette["gradient_to"])

    left_label = slide_data.get("left_label", "A").upper()
    left_text = slide_data.get("left_text", "")
    right_label = slide_data.get("right_label", "B").upper()
    right_text = slide_data.get("right_text", "")

    img = Image.new("RGB", (_W, _H), dark)
    blurred = bg.filter(ImageFilter.GaussianBlur(22))
    overlay = Image.new("RGBA", (_W, _H), (*dark, 210))
    img = Image.alpha_composite(blurred.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    # ── HEADER: pillar name + slide counter ────────────────────────
    draw.rectangle([(0, 0), (_W, _HEADER_H)], fill=acc)
    label_font = _font(_DISPLAY, 36)
    label = pillar["name"].upper()
    lw = draw.textlength(label, font=label_font)
    draw.text(((_W - lw) // 2, 42), label, font=label_font, fill=(255, 255, 255))

    count_font = _font(_BODY, 28)
    count_txt = f"{slide_num} / {total}"
    ctw = draw.textlength(count_txt, font=count_font)
    pill_x = _W - 80 - int(ctw) - 20
    pill_y = _HEADER_H - 68
    draw.rounded_rectangle([pill_x, pill_y, pill_x + int(ctw) + 20, pill_y + 48],
                           radius=24, fill=(0, 0, 0, 90))
    draw.text((pill_x + 10, pill_y + 10), count_txt, font=count_font, fill=(255, 255, 255))
    draw.rectangle([(0, _HEADER_H), (_W, _HEADER_H + 4)], fill=(255, 255, 255, 40))

    # ── SPLIT COLUMNS ──────────────────────────────────────────────
    body_top = _HEADER_H + 4
    body_bot = _H - _FOOTER_H
    mid_x = _W // 2

    # Left column — off-white bg, dark ink
    draw.rectangle([(0, body_top), (mid_x - 3, body_bot)], fill=(245, 245, 245))
    # Right column — accent bg
    draw.rectangle([(mid_x + 3, body_top), (_W, body_bot)], fill=acc)
    # Center divider
    draw.rectangle([(mid_x - 3, body_top), (mid_x + 3, body_bot)], fill=dark)

    # "VS" chip anchored on the divider
    vs_font = _font(_DISPLAY, 40)
    vs_txt = "VS"
    vsw = draw.textlength(vs_txt, font=vs_font)
    vs_r = 44
    vs_cy = body_top + 90
    draw.ellipse([mid_x - vs_r, vs_cy - vs_r, mid_x + vs_r, vs_cy + vs_r], fill=dark)
    draw.text((mid_x - vsw // 2, vs_cy - 26), vs_txt, font=vs_font, fill=(255, 255, 255))

    # Column labels — top of each column, sized to fit
    col_w = mid_x - 3
    col_pad = 44
    inner_w = col_w - 2 * col_pad
    label_size = 60
    label_font_l = _font(_DISPLAY, label_size)
    while draw.textlength(left_label, font=label_font_l) > inner_w and label_size > 30:
        label_size -= 4
        label_font_l = _font(_DISPLAY, label_size)
    r_size = 60
    label_font_r = _font(_DISPLAY, r_size)
    while draw.textlength(right_label, font=label_font_r) > inner_w and r_size > 30:
        r_size -= 4
        label_font_r = _font(_DISPLAY, r_size)

    # Text color on the accent (right) side is chosen by luminance —
    # bright accents (yellow/lime) need dark ink, dark accents need white.
    ar, ag, ab = acc
    accent_lum = (0.299 * ar + 0.587 * ag + 0.114 * ab) / 255.0
    right_ink = (20, 20, 25) if accent_lum > 0.6 else (255, 255, 255)
    right_rule = (20, 20, 25, 220) if accent_lum > 0.6 else (255, 255, 255, 220)

    label_y = vs_cy + vs_r + 40
    lw_l = draw.textlength(left_label, font=label_font_l)
    draw.text(((col_w - lw_l) // 2, label_y), left_label, font=label_font_l, fill=dark)
    lw_r = draw.textlength(right_label, font=label_font_r)
    draw.text((mid_x + 3 + (col_w - lw_r) // 2, label_y), right_label,
              font=label_font_r, fill=right_ink)

    # Divider under each label
    ul_y = label_y + label_size + 20
    draw.rectangle([(col_pad, ul_y), (col_w - col_pad, ul_y + 4)], fill=(*dark, 200))
    draw.rectangle([(mid_x + 3 + col_pad, ul_y), (_W - col_pad, ul_y + 4)], fill=right_rule)

    # Body text — same body font both sides, shrink-to-fit
    def _fit_and_draw(text: str, x_start: int, color: tuple[int, int, int]) -> None:
        text_w = inner_w
        body_size = 42
        body_font = _font(_BODY, body_size)
        lines = _wrap(text, body_font, text_w, draw)
        avail_h = body_bot - (ul_y + 40) - 30
        while len(lines) * (body_size + 12) > avail_h and body_size > 24:
            body_size -= 2
            body_font = _font(_BODY, body_size)
            lines = _wrap(text, body_font, text_w, draw)
        y = ul_y + 40
        for line in lines:
            draw.text((x_start + col_pad, y), line, font=body_font, fill=color)
            y += body_size + 12

    _fit_and_draw(left_text, 0, (25, 25, 30))
    _fit_and_draw(right_text, mid_x + 3, right_ink)

    # ── FOOTER ─────────────────────────────────────────────────────
    draw.rectangle([(0, _H - _FOOTER_H), (_W, _H)], fill=(*grad, 255))
    handle_font = _font(_BODY, 26)
    hw = draw.textlength(handle, font=handle_font)
    draw.text(((_W - hw) // 2, _H - _FOOTER_H + 38), handle,
              font=handle_font, fill=(200, 200, 200))
    if slide_num < total - 1:
        hint_font = _font(_BODY, 22)
        hint = "swipe →"
        hiw = draw.textlength(hint, font=hint_font)
        draw.text((_W - 80 - int(hiw), _H - _FOOTER_H + 40), hint,
                  font=hint_font, fill=(*acc, 180))

    return img


def _slide_cta(bg: Image.Image, text: str, pillar: dict, num: int, total: int,
               handle: str) -> Image.Image:
    """Slide 7: accent top block + dark body with CTA."""
    palette = pillar["visual_palette"]
    acc = _hex(palette["accent"])
    dark = _hex(palette["primary"])

    img = Image.new("RGB", (_W, _H), dark)
    blurred = bg.filter(ImageFilter.GaussianBlur(22))
    overlay = Image.new("RGBA", (_W, _H), (*dark, 195))
    img = Image.alpha_composite(blurred.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    margin = 80
    content_w = _W - 2 * margin

    # Large accent top block
    cta_header_h = 300
    draw.rectangle([(0, 0), (_W, cta_header_h)], fill=acc)

    # Save icon (stylized bookmark shape using rectangles)
    bm_x, bm_y = _W // 2 - 40, 60
    draw.rectangle([bm_x, bm_y, bm_x + 80, bm_y + 110], fill=(255, 255, 255))
    draw.polygon([(bm_x, bm_y + 110), (bm_x + 40, bm_y + 80),
                  (bm_x + 80, bm_y + 110)], fill=acc)

    # Counter in top block
    count_font = _font(_BODY, 28)
    count_txt = f"{num} / {total}"
    ctw = draw.textlength(count_txt, font=count_font)
    draw.text(((_W - ctw) // 2, cta_header_h - 52), count_txt,
              font=count_font, fill=(255, 255, 255, 200))

    draw.rectangle([(0, cta_header_h), (_W, cta_header_h + 5)],
                   fill=(255, 255, 255, 50))

    # CTA text in dark zone
    cta_font = _font(_DISPLAY, 68)
    lines = _wrap(text, cta_font, content_w, draw)
    dark_zone_h = _H - cta_header_h
    total_text_h = len(lines) * (68 + 20)
    y = cta_header_h + (dark_zone_h - total_text_h) // 2 - 40
    _draw_centered(draw, lines, cta_font, _W, y, (255, 255, 255), gap=20)

    # Handle
    handle_font = _font(_BODY, 28)
    hw = draw.textlength(handle, font=handle_font)
    draw.text(((_W - hw) // 2, _H - 60), handle,
              font=handle_font, fill=(*_hex(palette["accent"]), 180))

    # Left accent bar
    draw.rectangle([(0, cta_header_h + 5), (7, _H)], fill=acc)

    return img


# ── public API ──────────────────────────────────────────────────────────────

def compose_slide(bg_path: Path, slide_data: dict, slide_num: int, total_slides: int,
                  pillar: dict, output_path: Path, handle: str = "@modernmastery") -> Path:
    bg = _bg(bg_path)
    text = slide_data.get("text", "")

    if slide_num == 1:
        img = _slide_hook(bg, text, pillar, slide_num, total_slides, handle)
    elif slide_num == total_slides:
        img = _slide_cta(bg, text, pillar, slide_num, total_slides, handle)
    elif slide_data.get("layout") == "split":
        img = _slide_split(bg, slide_data, slide_num, total_slides, pillar, handle)
    else:
        img = _slide_content(bg, text, slide_num, total_slides, pillar, handle)

    img.save(output_path, format="JPEG", quality=93)
    return output_path


def compose_carousel(bg_path: Path, slides: list[dict], pillar: dict,
                     output_dir: Path, post_id: str,
                     handle: str = "@modernmastery") -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, slide in enumerate(slides, start=1):
        out = output_dir / f"{post_id}_slide_{i:02d}.jpg"
        compose_slide(bg_path, slide, i, len(slides), pillar, out, handle)
        paths.append(out)
        print(f"    slide {i}/{len(slides)} ✓")
    return paths
