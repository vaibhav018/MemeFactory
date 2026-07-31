#!/usr/bin/env python3
"""
LOGO MAKER for @bhogeswar_rao_garu
==================================
Draws the page badge procedurally with Pillow so it can be tweaked and
regenerated anytime.

Outputs (to assets/Logo/):
  logo_badge_1024.png   - full round badge with curved rim text (profile pic)
  logo_watermark.png    - simplified face-only roundel for stamping on memes

Design: emoji-style jolly yellow uncle (side-parted hair, round glasses,
thick mustache, big grin) on a black badge with yellow rings - matches the
meme format palette (yellow 255,222,0 / white / black).
"""

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BASE = Path(r"C:\Users\ASUS\Documents\MemeFactory")
OUT_DIR = BASE / "assets" / "Logo"
OUT_DIR.mkdir(parents=True, exist_ok=True)

YELLOW = (255, 222, 0, 255)
DARK_YELLOW = (235, 190, 0, 255)
WHITE = (255, 255, 255, 255)
BLACK = (12, 12, 12, 255)
FONT_PATH = r"C:\Windows\Fonts\impact.ttf"

S = 1024                      # master canvas size
C = S // 2                    # center


# ---------------------------------------------------------------- helpers
def arc_text(img, text, radius, center, font, fill, top=True, tracking_deg=2.0):
    """Draw text curved along a circle. top=True curves over the top."""
    # measure each char to get its angular width
    probe = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    widths = [max(probe.textlength(ch, font=font), font.size * 0.28) for ch in text]
    angles = [math.degrees(w / radius) + tracking_deg for w in widths]
    total = sum(angles)

    # starting angle so the text is centered on top (-90) or bottom (+90)
    mid = -90 if top else 90
    direction = 1 if top else -1
    theta = mid - direction * total / 2

    for ch, ang in zip(text, angles):
        theta_c = theta + direction * ang / 2          # char center angle
        # render the char on its own tile, rotate, paste
        tile_s = font.size * 3
        tile = Image.new("RGBA", (tile_s, tile_s), (0, 0, 0, 0))
        td = ImageDraw.Draw(tile)
        td.text((tile_s / 2, tile_s / 2), ch, font=font, fill=fill, anchor="mm")
        rot = -(theta_c + 90) if top else -(theta_c - 90)
        tile = tile.rotate(rot, resample=Image.Resampling.BICUBIC, expand=False)
        x = center[0] + radius * math.cos(math.radians(theta_c))
        y = center[1] + radius * math.sin(math.radians(theta_c))
        img.alpha_composite(tile, (int(x - tile_s / 2), int(y - tile_s / 2)))
        theta += direction * ang


def circle(draw, cx, cy, r, **kw):
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], **kw)


def rotated_ellipse(img, cx, cy, w, h, angle, fill):
    """Paste a rotated filled ellipse onto img (for the mustache halves)."""
    pad = 8
    tile = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    td = ImageDraw.Draw(tile)
    td.ellipse([pad, pad, pad + w, pad + h], fill=fill)
    tile = tile.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)
    img.alpha_composite(tile, (int(cx - tile.width / 2), int(cy - tile.height / 2)))


# ---------------------------------------------------------------- the face
def draw_face(img, cx, cy, R):
    """Jolly uncle face, emoji-style, scaled to radius R."""
    d = ImageDraw.Draw(img)
    u = R / 390.0  # unit scale (design was sketched at R=390)

    # head
    circle(d, cx, cy, R, fill=YELLOW)

    # hair: symmetric black cap over the top with a side parting
    hair = Image.new("RGBA", img.size, (0, 0, 0, 0))
    hd = ImageDraw.Draw(hair)
    hd.chord([cx - R, cy - R, cx + R, cy + R], 200, 340, fill=BLACK)
    # side parting (thin yellow line inside the cap, left of center)
    hd.line([cx - 95 * u, cy - 155 * u, cx - 150 * u, cy - 280 * u],
            fill=YELLOW, width=int(14 * u))
    img.alpha_composite(hair)

    # ears sticking out
    circle(d, cx - R + 6 * u, cy + 20 * u, 42 * u, fill=YELLOW, outline=DARK_YELLOW, width=int(6 * u))
    circle(d, cx + R - 6 * u, cy + 20 * u, 42 * u, fill=YELLOW, outline=DARK_YELLOW, width=int(6 * u))

    # glasses: round black frames with happy closed eyes
    eye_y = cy - 20 * u
    for ex in (cx - 118 * u, cx + 118 * u):
        circle(d, ex, eye_y, 82 * u, outline=BLACK, width=int(14 * u))
        # happy closed-eye arc inside each lens
        r_eye = 38 * u
        d.arc([ex - r_eye, eye_y - r_eye + 12 * u, ex + r_eye, eye_y + r_eye + 12 * u],
              200, 340, fill=BLACK, width=int(12 * u))
    # bridge + temples
    d.line([cx - 36 * u, eye_y - 16 * u, cx + 36 * u, eye_y - 16 * u], fill=BLACK, width=int(14 * u))
    d.line([cx - 200 * u, eye_y - 8 * u, cx - R + 16 * u, eye_y - 18 * u], fill=BLACK, width=int(12 * u))
    d.line([cx + 200 * u, eye_y - 8 * u, cx + R - 16 * u, eye_y - 18 * u], fill=BLACK, width=int(12 * u))

    # nose: small rounded blob
    circle(d, cx, cy + 80 * u, 34 * u, fill=DARK_YELLOW)

    # big grin (draw before mustache so the mustache sits on top of it)
    r_sm = 135 * u
    d.arc([cx - r_sm, cy + 60 * u, cx + r_sm, cy + 60 * u + 2 * r_sm],
          35, 145, fill=BLACK, width=int(18 * u))

    # thick mustache: two rotated ellipses meeting under the nose
    rotated_ellipse(img, cx - 92 * u, cy + 138 * u, int(190 * u), int(78 * u), 18, BLACK)
    rotated_ellipse(img, cx + 92 * u, cy + 138 * u, int(190 * u), int(78 * u), -18, BLACK)

    # rosy cheeks
    circle(d, cx - 210 * u, cy + 90 * u, 34 * u, fill=DARK_YELLOW)
    circle(d, cx + 210 * u, cy + 90 * u, 34 * u, fill=DARK_YELLOW)


# ---------------------------------------------------------------- badge
def make_badge():
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # badge base + rings
    circle(d, C, C, 505, fill=BLACK)
    circle(d, C, C, 498, outline=YELLOW, width=14)
    circle(d, C, C, 408, outline=YELLOW, width=6)

    # face inside the inner ring
    draw_face(img, C, C + 6, 330)

    # curved rim text
    font_top = ImageFont.truetype(FONT_PATH, 86)
    font_bot = ImageFont.truetype(FONT_PATH, 66)
    arc_text(img, "BHOGESWAR RAO GARU", radius=448, center=(C, C),
             font=font_top, fill=WHITE, top=True)
    arc_text(img, "TELUGU MEMES", radius=448, center=(C, C),
             font=font_bot, fill=YELLOW, top=False, tracking_deg=3.0)

    # small star separators on the sides
    star_font = ImageFont.truetype(FONT_PATH, 60)
    for sx in (C - 452, C + 452):
        d.text((sx, C), "*", font=star_font, fill=YELLOW, anchor="mm")

    out = OUT_DIR / "logo_badge_1024.png"
    img.save(out)
    print(f">> Badge saved: {out}")
    return out


def make_watermark():
    """Face-only roundel, reads clearly even at ~120px on a meme."""
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    circle(d, C, C, 505, fill=BLACK)
    circle(d, C, C, 496, outline=YELLOW, width=20)
    draw_face(img, C, C + 8, 400)
    img = img.resize((512, 512), Image.Resampling.LANCZOS)
    out = OUT_DIR / "logo_watermark.png"
    img.save(out)
    print(f">> Watermark saved: {out}")
    return out


# ------------------------------------------------- photo mash-up variants
PHOTO_PATH = OUT_DIR / "sontham-bhogeswararao.gif"
# head-and-shoulders circle in the source frame (640x360): center + radius
PHOTO_CENTER = (312, 140)
PHOTO_RADIUS = 135


def load_photo_circle(diameter: int) -> Image.Image:
    """First GIF frame -> sharpened circular face crop at the given diameter."""
    from PIL import ImageFilter

    src = Image.open(PHOTO_PATH)
    src.seek(0)
    src = src.convert("RGB")
    cx, cy = PHOTO_CENTER
    r = PHOTO_RADIUS
    crop = src.crop((cx - r, cy - r, cx + r, cy + r))
    crop = crop.resize((diameter, diameter), Image.Resampling.LANCZOS)
    # GIF frames are soft; unsharp mask recovers some crispness after upscale
    crop = crop.filter(ImageFilter.UnsharpMask(radius=4, percent=120, threshold=2))

    mask = Image.new("L", (diameter, diameter), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, diameter, diameter], fill=255)
    out = Image.new("RGBA", (diameter, diameter), (0, 0, 0, 0))
    out.paste(crop, (0, 0), mask)
    return out


def make_photo_badge():
    """Badge with the real Bhogeswar Rao photo instead of the cartoon face."""
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    circle(d, C, C, 505, fill=BLACK)
    circle(d, C, C, 498, outline=YELLOW, width=14)

    face_d = 2 * 396
    photo = load_photo_circle(face_d)
    img.alpha_composite(photo, (C - face_d // 2, C - face_d // 2))
    circle(d, C, C, 400, outline=YELLOW, width=10)   # ring framing the photo

    font_top = ImageFont.truetype(FONT_PATH, 86)
    font_bot = ImageFont.truetype(FONT_PATH, 66)
    arc_text(img, "BHOGESWAR RAO GARU", radius=448, center=(C, C),
             font=font_top, fill=WHITE, top=True)
    arc_text(img, "TELUGU MEMES", radius=448, center=(C, C),
             font=font_bot, fill=YELLOW, top=False, tracking_deg=3.0)

    star_font = ImageFont.truetype(FONT_PATH, 60)
    for sx in (C - 452, C + 452):
        d.text((sx, C), "*", font=star_font, fill=YELLOW, anchor="mm")

    out = OUT_DIR / "logo_photo_badge_1024.png"
    img.save(out)
    print(f">> Photo badge saved: {out}")
    return out


def make_photo_watermark():
    """Photo roundel with yellow ring - the corner stamp for memes."""
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    face_d = 2 * 496
    photo = load_photo_circle(face_d)
    img.alpha_composite(photo, (C - face_d // 2, C - face_d // 2))
    circle(d, C, C, 496, outline=YELLOW, width=24)
    img = img.resize((512, 512), Image.Resampling.LANCZOS)
    out = OUT_DIR / "logo_photo_watermark.png"
    img.save(out)
    print(f">> Photo watermark saved: {out}")
    return out


if __name__ == "__main__":
    make_badge()
    make_watermark()
    if PHOTO_PATH.exists():
        make_photo_badge()
        make_photo_watermark()
    print("Done.")
