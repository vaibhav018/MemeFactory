"""Step 4 (06:30) - composite the final meme image.

Reads data/reaction_selection.json (written by reaction_picker.py), overlays
the top caption + punchline + watermark onto each reaction image, and saves
1080x1350 Instagram-ready JPEGs to the local memes directory. drive_uploader.py
handles pushing the finished files to the Drive queue folder.

Run standalone for isolated testing:
    python meme_compositor.py
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

from config_loader import get_logger, load_config


class FallbackFont:
    """Punchlines are intentionally Hinglish - Telugu and Latin characters mixed
    in the same string. A single font file rarely covers both (Noto's per-script
    fonts in particular ship Telugu glyphs only, zero Latin). This picks, per
    character, the first candidate font whose cmap actually contains that glyph,
    falling back to PIL's built-in font (which covers ASCII) as a last resort.
    """

    def __init__(self, candidate_paths: list[str], size: int, logger):
        self.stages: list[tuple[ImageFont.FreeTypeFont, dict | None]] = []
        seen = set()
        for path in candidate_paths:
            if not path or path in seen or not Path(path).exists():
                continue
            seen.add(path)
            try:
                pil_font = ImageFont.truetype(path, size=size)
                cmap = TTFont(path, fontNumber=0).getBestCmap()
            except Exception as exc:
                logger.warning(f"Could not load font {path}: {exc}")
                continue
            self.stages.append((pil_font, cmap))

        if not self.stages:
            logger.warning(
                f"None of {candidate_paths} could be loaded - falling back entirely to PIL's "
                "default font (non-Latin glyphs will NOT render). See assets/fonts/SETUP_FONTS.txt."
            )
        # Final catch-all so an uncovered character still renders as *something*.
        self.stages.append((ImageFont.load_default(size=size), None))
        self.primary = self.stages[0][0]

    def font_for_char(self, ch: str) -> ImageFont.FreeTypeFont:
        if ch.isspace():
            return self.primary
        cp = ord(ch)
        for font, cmap in self.stages:
            if cmap is None or cp in cmap:
                return font
        return self.stages[-1][0]

    def text_width(self, text: str) -> float:
        return sum(self.font_for_char(ch).getlength(ch) for ch in text)

    def line_height(self) -> int:
        ascent, descent = self.primary.getmetrics()
        return ascent + descent


# Neither the Telugu font nor Pillow's built-in fallback ship color emoji glyphs,
# so drawing these produces ugly tofu boxes. Strip them rather than render a box.
_UNRENDERABLE_RANGES = [
    (0x1F300, 0x1FAFF),  # emoji & pictographs
    (0x2600, 0x27BF),    # misc symbols and dingbats
    (0xFE00, 0xFE0F),    # variation selectors
    (0x1F1E6, 0x1F1FF),  # regional indicator (flag) letters
]


def strip_unrenderable(text: str) -> str:
    return "".join(
        ch for ch in text if not any(lo <= ord(ch) <= hi for lo, hi in _UNRENDERABLE_RANGES)
    ).strip()


def cover_resize_crop(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Resize+center-crop an image to exactly fill target_w x target_h (cover fit)."""
    src_w, src_h = img.size
    scale = max(target_w / src_w, target_h / src_h)
    new_w, new_h = round(src_w * scale), round(src_h * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)

    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    return img.crop((left, top, left + target_w, top + target_h))


def wrap_text(text: str, font: FallbackFont, max_width_px: int) -> list[str]:
    """Greedy word-wrap using actual rendered glyph widths (mixed-script aware)."""
    words = text.split()
    if not words:
        return [""]

    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        trial = f"{current} {word}"
        if font.text_width(trial) <= max_width_px:
            current = trial
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def draw_stroked_text_block(
    draw: ImageDraw.ImageDraw,
    lines: list[str],
    font: FallbackFont,
    color: tuple[int, int, int],
    stroke_color: tuple[int, int, int],
    stroke_width: int,
    canvas_w: int,
    y: int,
    line_spacing: int = 10,
) -> int:
    """Draw centered, stroked text lines starting at y, picking a font per character
    so mixed Telugu+Latin punchlines render correctly. Returns the y after the block."""
    line_h = font.line_height()
    for line in lines:
        line_w = font.text_width(line)
        x = (canvas_w - line_w) / 2
        for ch in line:
            char_font = font.font_for_char(ch)
            draw.text(
                (x, y),
                ch,
                font=char_font,
                fill=color,
                stroke_width=stroke_width,
                stroke_fill=stroke_color,
            )
            x += char_font.getlength(ch)
        y += line_h + line_spacing
    return y


def composite_meme(story: dict[str, Any], cfg: dict[str, Any], logger) -> str | None:
    comp_cfg = cfg["compositor"]
    width, height = comp_cfg["output_width"], comp_cfg["output_height"]

    reaction = story.get("reaction_image")
    if not reaction or not reaction.get("local_path"):
        logger.error(f"Story missing a reaction image, skipping: {story.get('top_caption', '')[:60]}")
        return None

    try:
        base = Image.open(reaction["local_path"]).convert("RGB")
    except (OSError, FileNotFoundError) as exc:
        logger.error(f"Could not open reaction image {reaction['local_path']}: {exc}")
        return None

    canvas = cover_resize_crop(base, width, height)
    draw = ImageDraw.Draw(canvas)

    top_cfg = comp_cfg["top_caption"]
    bottom_cfg = comp_cfg["bottom_caption"]
    wm_cfg = comp_cfg["watermark"]

    top_font = FallbackFont([top_cfg["font_path"], top_cfg["fallback_font_path"]], top_cfg["font_size"], logger)
    bottom_font = FallbackFont(
        [bottom_cfg["font_path"], bottom_cfg["fallback_font_path"]], bottom_cfg["font_size"], logger
    )
    wm_font = FallbackFont([wm_cfg["font_path"]], wm_cfg["font_size"], logger)

    max_top_w = int(width * top_cfg["max_width_ratio"])
    max_bottom_w = int(width * bottom_cfg["max_width_ratio"])

    top_lines = wrap_text(strip_unrenderable(story.get("top_caption", "")), top_font, max_top_w)
    bottom_lines = wrap_text(strip_unrenderable(story.get("punchline", "")), bottom_font, max_bottom_w)

    draw_stroked_text_block(
        draw, top_lines, top_font,
        tuple(top_cfg["color"]), tuple(top_cfg["stroke_color"]), top_cfg["stroke_width"],
        width, top_cfg["top_margin"],
    )

    # Bottom block is anchored from the bottom margin upward.
    total_bottom_h = bottom_font.line_height() * len(bottom_lines) + 10 * (len(bottom_lines) - 1)
    start_y = height - bottom_cfg["bottom_margin"] - total_bottom_h
    draw_stroked_text_block(
        draw, bottom_lines, bottom_font,
        tuple(bottom_cfg["color"]), tuple(bottom_cfg["stroke_color"]), bottom_cfg["stroke_width"],
        width, start_y,
    )

    # Watermark, bottom-right.
    wm_text = wm_cfg["text"]
    wm_w, wm_h = wm_font.text_width(wm_text), wm_font.line_height()
    wm_x = width - wm_cfg["margin"] - wm_w
    wm_y = height - wm_cfg["margin"] - wm_h
    for ch in wm_text:
        char_font = wm_font.font_for_char(ch)
        draw.text((wm_x, wm_y), ch, font=char_font, fill=tuple(wm_cfg["color"]))
        wm_x += char_font.getlength(ch)

    out_dir = Path(cfg["paths"]["local_memes_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    ext = "jpg" if comp_cfg["output_format"].upper() == "JPEG" else "png"
    safe_emotion = story.get("emotion", "meme")
    out_name = f"meme_{safe_emotion}_{abs(hash(story.get('url', story.get('top_caption', ''))))}.{ext}"
    out_path = out_dir / out_name

    save_kwargs = {"quality": comp_cfg["output_quality"]} if ext == "jpg" else {}
    canvas.save(out_path, comp_cfg["output_format"], **save_kwargs)
    logger.info(f"Composited meme -> {out_path}")
    return str(out_path)


def load_reaction_selection(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    path = cfg["_root"] / "data" / "reaction_selection.json"
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []


def run_pipeline_step(cfg: dict[str, Any], logger) -> list[str]:
    """Composite every story+reaction pair into a finished meme. Called by CLI and scheduler.py."""
    stories = load_reaction_selection(cfg)
    if not stories:
        logger.warning("No stories with reaction images found - run reaction_picker.py first")
        return []

    output_paths = []
    for story in stories:
        try:
            path = composite_meme(story, cfg, logger)
        except Exception as exc:
            logger.error(f"Compositing failed for '{story.get('top_caption', '')[:60]}': {exc}")
            continue
        if path:
            output_paths.append(path)

    logger.info(f"Composited {len(output_paths)}/{len(stories)} memes")
    return output_paths


def main() -> list[str]:
    cfg = load_config()
    logger = get_logger("meme_compositor", cfg)
    return run_pipeline_step(cfg, logger)


if __name__ == "__main__":
    main()
