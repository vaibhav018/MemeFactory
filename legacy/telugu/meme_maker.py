"""
Mana Telugu Trolls — Meme Compositor
Run locally (or anywhere Pillow + a font are available).

    pip install pillow
    python meme_maker.py

It overlays top/bottom text + a corner handle onto a reaction image,
producing a classic Telugu-meme layout (black bars optional).
This is the same step the daily pipeline calls automatically.
"""

from PIL import Image, ImageDraw, ImageFont
import textwrap, os

# ---------- CONFIG ----------
REACTION_IMG = "reaction.jpg"        # your downloaded reaction face
OUTPUT       = "meme_out.jpg"
TOP_TEXT     = "Peddi Day 5 boxoffice report chudagane"
BOTTOM_TEXT  = "Antha lo antha le mawa"
HANDLE       = "@mana_telugu_trolls"
FONT_PATH    = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"  # change if needed
TARGET_W     = 1080                  # IG square-ish width
# ----------------------------

def fit_font(size):
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except OSError:
        return ImageFont.load_default()

def draw_outlined(draw, xy, text, font, fill="white", outline="black", w=3):
    x, y = xy
    for dx in range(-w, w + 1):
        for dy in range(-w, w + 1):
            draw.text((x + dx, y + dy), text, font=font, fill=outline)
    draw.text((x, y), text, font=font, fill=fill)

def add_caption_bar(base, text, position, font_size=54):
    """position = 'top' or 'bottom'. Adds a black bar with centered text."""
    if not text:
        return base
    font = fit_font(font_size)
    lines = textwrap.wrap(text, width=28) or [""]
    line_h = font_size + 14
    bar_h = line_h * len(lines) + 24

    new_h = base.height + bar_h
    canvas = Image.new("RGB", (base.width, new_h), "black")
    draw = ImageDraw.Draw(canvas)

    if position == "top":
        canvas.paste(base, (0, bar_h))
        y = 12
    else:  # bottom
        canvas.paste(base, (0, 0))
        y = base.height + 12

    for ln in lines:
        bbox = draw.textbbox((0, 0), ln, font=font)
        tw = bbox[2] - bbox[0]
        draw.text(((base.width - tw) // 2, y), ln, font=font, fill="white")
        y += line_h
    return canvas

def main():
    if not os.path.exists(REACTION_IMG):
        raise SystemExit(f"Put your reaction image at ./{REACTION_IMG} first.")

    img = Image.open(REACTION_IMG).convert("RGB")
    # normalize width
    if img.width != TARGET_W:
        ratio = TARGET_W / img.width
        img = img.resize((TARGET_W, int(img.height * ratio)))

    img = add_caption_bar(img, TOP_TEXT, "top")
    img = add_caption_bar(img, BOTTOM_TEXT, "bottom")

    # handle watermark, bottom-right
    draw = ImageDraw.Draw(img)
    hfont = fit_font(34)
    bbox = draw.textbbox((0, 0), HANDLE, font=hfont)
    hw = bbox[2] - bbox[0]
    draw_outlined(draw, (img.width - hw - 24, img.height - 56),
                  HANDLE, hfont, fill="#FFD24A", outline="black", w=2)

    img.save(OUTPUT, quality=92)
    print(f"Saved {OUTPUT}  ({img.width}x{img.height})")

if __name__ == "__main__":
    main()
