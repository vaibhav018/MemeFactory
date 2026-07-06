#!/usr/bin/env python3
"""
MEME FACTORY - "Mana Telugu Trolls" style news meme generator
=============================================================
Format learned from assets/Reference Memes:
  - Full-bleed photo filling the frame edge-to-edge (no letterboxing)
  - Black bar on TOP with multi-line ALL-CAPS condensed text
  - Black bar on BOTTOM with the punchline/commentary
  - Two-tone text: WHITE for the factual setup, YELLOW for the punchline
  - Optional logo badge in a corner

It can also auto-download a news photo for the topic (DuckDuckGo image
search) so the meme uses a real related image, e.g. "ED auctions private jet".

Usage:
  python meme_factory.py                          -> uses MEME config below
  Edit the MEME dict to change content.
"""

import io
import os
import re
import sys
import textwrap
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from PIL import Image, ImageDraw, ImageFont

# ============================== PATHS ==============================
BASE = Path(__file__).resolve().parent      # portable: repo root, any OS
REACTION_DIR = BASE / "assets" / "Reaction images"
DOWNLOAD_DIR = BASE / "assets" / "Downloaded"
OUTPUT_DIR = BASE / "Generated_Memes"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ============================== STYLE ==============================
CANVAS_W = 1080
CANVAS_H = 1350                      # Instagram 4:5 portrait
WHITE = (255, 255, 255)
YELLOW = (255, 222, 0)               # mana-telugu-trolls style yellow
BLACK = (10, 10, 10)
# Anton (bundled, open license) - same condensed ALL-CAPS look as Impact,
# works on Windows and Linux (GitHub Actions) alike
FONT_PATH = str(BASE / "assets" / "fonts" / "Anton-Regular.ttf")
LOGO_PATH = BASE / "assets" / "Logo" / "logo_photo_watermark.png"
FACE_MODEL_PATH = BASE / "assets" / "models" / "face_detection_yunet_2023mar.onnx"
LOGO_SIZE = 130                      # px, stamped in the photo's top-right corner
LOGO_MARGIN = 18
FONT_MAX = 58                        # starting font size
FONT_MIN = 34                        # shrink to fit down to this
LINE_SPACING = 1.08                  # tight leading like the references
BAR_PAD_Y = 22                       # vertical padding inside each bar
SIDE_PAD = 30                        # min horizontal padding for text

EMOJI_RE = re.compile(
    "[" "\U0001F300-\U0001FAFF" "\U00002600-\U000027BF" "\U0001F1E6-\U0001F1FF" "]+"
)

# Only accept photos hosted by known Indian news/entertainment outlets - image
# search titles can match the query while the scraped "image" for that page is
# an unrelated ad/sidebar/stock photo. Restricting to trusted publishers is a
# second, independent check on top of the title-relevance filter.
TRUSTED_NEWS_DOMAINS = {
    "sakshi.com", "123telugu.com", "tv9telugu.com", "ap7am.com", "thehansindia.com",
    "newindianexpress.com", "deccanchronicle.com", "thehindu.com", "thgim.com",
    "thebetterandhra.com", "gulte.com", "greatandhra.com", "telugu360.com",
    "andhrajyothy.com", "eenadu.net", "ntnews.com", "v6velugu.com",
    "ndtv.com", "indiatoday.in", "timesofindia.indiatimes.com", "indianexpress.com",
    "hindustantimes.com", "news18.com", "abplive.com", "moneycontrol.com",
    "business-standard.com", "livemint.com", "financialexpress.com",
    "outlookindia.com", "outlookbusiness.com", "assettype.com",
    "zeenews.india.com", "republicworld.com", "wionews.com", "bhaskar.com",
    "filmibeat.com", "telanganatoday.com",
}


def _is_trusted_domain(url: str) -> bool:
    try:
        netloc = urlparse(url).netloc.lower().split(":")[0]
    except Exception:
        return False
    return any(netloc == d or netloc.endswith("." + d) for d in TRUSTED_NEWS_DOMAINS)

# ============================== MEME CONTENT ==============================
# Each caption block is a list of (text, color) lines.  Text is auto-wrapped
# and auto-shrunk to fit.  WHITE = factual setup, YELLOW = punch/key stat.
MEME = {
    # what to search for when downloading the photo (make it specific!)
    "image_query": "Enforcement Directorate auction private jet Hyderabad Hawker 800A",
    # or force a local file and skip downloading:
    "image_file": None,              # e.g. str(REACTION_DIR / "some.jpg")
    "top": [
        ("Enforcement Directorate Hyderabad office auctioned", WHITE),
        ("a private jet for Rs 3 Cr, the jet was seized", YELLOW),
        ("during a money laundering scam in 2025", YELLOW),
    ],
    "bottom": [
        ("You can buy a private jet in Hyd for 3 Cr", WHITE),
        ("Model - Hawker 800A jet plane", YELLOW),
        ("Actual price - 15 to 25 Crores", YELLOW),
    ],
    "slug": "ed_jet",                # used in the output filename
}


# ============================== IMAGE FETCH ==============================
def fetch_news_image(query: str, save_dir: Path, max_tries: int = 10,
                     must_contain: str | None = None) -> Path | None:
    """Search DuckDuckGo images for `query` and download the first usable photo.

    Strict by design: if `must_contain` is given, only title-matching results
    are considered at all (no falling through to unrelated images), and every
    candidate must also come from a known news/entertainment domain
    (TRUSTED_NEWS_DOMAINS) - image search occasionally mismatches a page's
    title against an unrelated ad/sidebar photo scraped from that page, so
    relying on the title alone isn't enough. Returns None (caller falls back
    to a local reaction image) rather than ever using an unrelated/unvetted
    photo. safesearch is forced to "on" regardless of query content.
    Biased toward large source images (size="Large") since the final canvas
    is 1080x1350 - small source photos would otherwise get visibly upscaled.
    """
    try:
        import requests
        from ddgs import DDGS
    except ImportError:
        print("!! ddgs/requests not installed - run: pip install --user ddgs requests")
        return None

    print(f">> Searching images for: {query}")
    try:
        results = list(DDGS().images(query, max_results=max_tries * 3, size="Large", safesearch="on"))
    except Exception as e:
        print(f"!! Image search failed: {e}")
        return None

    if must_contain:
        key = must_contain.lower()
        results = [r for r in results if key in (r.get("title") or "").lower()]
        print(f">> Relevance filter '{must_contain}': {len(results)} title-matching results")

    results = [r for r in results if _is_trusted_domain(r.get("image") or "")]
    print(f">> Trusted-domain filter: {len(results)} from known news sources")

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    tried = 0
    for r in results:
        if tried >= max_tries:
            break
        url = r.get("image")
        if not url:
            continue
        tried += 1
        try:
            resp = requests.get(url, headers=headers, timeout=12)
            resp.raise_for_status()
            img = Image.open(io.BytesIO(resp.content))
            img.load()
            w, h = img.size
            if w < 900 or h < 650:          # skip thumbnails/small images that'd visibly upscale to 1080x1350
                print(f"   - too small ({w}x{h}), skipping")
                continue
            safe = re.sub(r"\W+", "_", query)[:50]
            out = save_dir / f"{safe}.jpg"
            if img.format == "JPEG" and img.mode == "RGB":
                # Write the original bytes directly - re-encoding here would
                # be a second lossy JPEG generation before render_meme's own.
                out.write_bytes(resp.content)
            else:
                img.convert("RGB").save(out, quality=95, optimize=True)
            print(f">> Downloaded {w}x{h}: {url[:80]}")
            print(f">> Saved to: {out}")
            return out
        except Exception as e:
            print(f"   - failed ({str(e)[:60]}), trying next")
    print("!! Could not download any usable image")
    return None


# ============================== TEXT LAYOUT ==============================
def strip_emoji(t: str) -> str:
    """Remove glyphs Impact can't render: emoji, plus currency/quote fixups."""
    t = EMOJI_RE.sub("", t)
    t = t.replace("₹", "Rs ").replace("‘", "'").replace("’", "'")
    t = t.replace("“", '"').replace("”", '"').replace("—", "-")
    return re.sub(r"\s+", " ", t).strip()


def wrap_line(draw, text, font, max_w):
    """Word-wrap one logical line into as many physical lines as needed."""
    words, lines, cur = text.split(), [], ""
    for w in words:
        cand = f"{cur} {w}".strip()
        if draw.textlength(cand, font=font) <= max_w or not cur:
            cur = cand
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def layout_block(draw, block, max_w):
    """
    Fit a caption block: find the biggest font size (<= FONT_MAX) where every
    wrapped physical line fits max_w and the block stays reasonable.
    Returns (font, [(physical_line, color), ...], block_height).
    """
    block = [(strip_emoji(t).upper(), c) for t, c in block if strip_emoji(t)]
    for size in range(FONT_MAX, FONT_MIN - 1, -2):
        font = ImageFont.truetype(FONT_PATH, size)
        phys = []
        for text, color in block:
            for line in wrap_line(draw, text, font, max_w):
                phys.append((line, color))
        line_h = int(size * LINE_SPACING)
        height = line_h * len(phys) + BAR_PAD_Y * 2
        # keep both bars together under ~40% of the canvas
        if height <= CANVAS_H * 0.22 or size == FONT_MIN:
            return font, phys, height, line_h
    # unreachable, loop always returns
    raise AssertionError


def draw_block(draw, phys_lines, font, line_h, y):
    for line, color in phys_lines:
        w = draw.textlength(line, font=font)
        x = (CANVAS_W - w) // 2
        draw.text((x, y), line, font=font, fill=color)
        y += line_h


# ============================== COMPOSITE ==============================
def _detect_faces(img: Image.Image):
    """Returns face boxes [(x, y, w, h), ...] in the original image's coordinates.
    Returns [] if the face model isn't available or no faces are found -
    callers must treat that as "fall back to center crop", not an error.

    Uses OpenCV's bundled YuNet detector (cv2.FaceDetectorYN) - the modern
    replacement for the old Haar cascade API, which OpenCV 5.x removed.
    """
    if not FACE_MODEL_PATH.exists():
        return []
    try:
        import cv2
        import numpy as np
        arr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        h, w = arr.shape[:2]
        detector = cv2.FaceDetectorYN_create(str(FACE_MODEL_PATH), "", (w, h))
        _, faces = detector.detect(arr)
        if faces is None:
            return []
        return [tuple(f[:4]) for f in faces]
    except Exception as exc:
        print(f"   - face detection unavailable ({exc}), using center crop")
        return []


def _crop_offset(faces, scale, new_w, new_h, target_w, target_h) -> tuple[int, int]:
    """Crop position biased to keep detected faces in frame. Falls back to a
    plain center crop when no faces were found."""
    default_left = (new_w - target_w) // 2
    default_top = (new_h - target_h) // 2
    if not len(faces):
        return default_left, default_top

    xs1 = [int(x * scale) for (x, y, w, h) in faces]
    ys1 = [int(y * scale) for (x, y, w, h) in faces]
    xs2 = [int((x + w) * scale) for (x, y, w, h) in faces]
    ys2 = [int((y + h) * scale) for (x, y, w, h) in faces]
    faces_cx = (min(xs1) + max(xs2)) // 2
    faces_cy = (min(ys1) + max(ys2)) // 2

    left = max(0, min(faces_cx - target_w // 2, new_w - target_w))
    top = max(0, min(faces_cy - target_h // 2, new_h - target_h))
    return left, top


def cover_crop(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Resize + crop so the image fills target area completely (full bleed).

    Crop position is face-aware: a plain center-crop was chopping off heads
    on portrait photos and multi-person collages whenever the source aspect
    ratio required cropping a lot of vertical space. Detected faces (via
    OpenCV's bundled Haar cascade - free, no download, no API) are kept in
    frame instead; falls back to the old center-crop if none are found.
    """
    img = img.convert("RGB")
    faces = _detect_faces(img)
    scale = max(target_w / img.width, target_h / img.height)
    new_w, new_h = round(img.width * scale), round(img.height * scale)
    new = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    left, top = _crop_offset(faces, scale, new_w, new_h, target_w, target_h)
    return new.crop((left, top, left + target_w, top + target_h))


def render_meme(image_path, top_block, bottom_block, out_path):
    """bottom_block may be empty/None - then the photo runs to the bottom edge."""
    canvas = Image.new("RGB", (CANVAS_W, CANVAS_H), BLACK)
    draw = ImageDraw.Draw(canvas)
    max_text_w = CANVAS_W - SIDE_PAD * 2

    top_font, top_phys, top_h, top_lh = layout_block(draw, top_block, max_text_w)
    if bottom_block:
        bot_font, bot_phys, bot_h, bot_lh = layout_block(draw, bottom_block, max_text_w)
    else:
        bot_phys, bot_h = [], 0

    # photo fills everything between the two bars, edge to edge
    photo_h = CANVAS_H - top_h - bot_h
    photo = cover_crop(Image.open(image_path), CANVAS_W, photo_h)
    canvas.paste(photo, (0, top_h))

    # page logo badge in the photo's top-right corner
    if LOGO_PATH.exists():
        logo = Image.open(LOGO_PATH).convert("RGBA")
        logo.thumbnail((LOGO_SIZE, LOGO_SIZE), Image.Resampling.LANCZOS)
        canvas.paste(logo, (CANVAS_W - LOGO_SIZE - LOGO_MARGIN, top_h + LOGO_MARGIN), logo)

    draw_block(draw, top_phys, top_font, top_lh, BAR_PAD_Y)
    if bot_phys:
        draw_block(draw, bot_phys, bot_font, bot_lh, top_h + photo_h + BAR_PAD_Y)

    canvas.save(out_path, quality=97, optimize=True)
    print(f">> Meme saved: {out_path}")
    return out_path


# ============================== MAIN ==============================
def main():
    print("=" * 70)
    print("MEME FACTORY - news meme generator (Mana Telugu Trolls style)")
    print("=" * 70)

    # 1. get the photo
    if MEME.get("image_file"):
        image_path = Path(MEME["image_file"])
        print(f">> Using local image: {image_path}")
    else:
        image_path = fetch_news_image(MEME["image_query"], DOWNLOAD_DIR)
        if image_path is None:
            print("!! Falling back to a reaction image")
            candidates = list(REACTION_DIR.glob("*.jpg"))
            if not candidates:
                sys.exit("No fallback images available.")
            import random
            image_path = random.choice(candidates)
            print(f">> Fallback: {image_path.name}")

    # 2. render
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = OUTPUT_DIR / f"meme_{MEME['slug']}_{ts}.jpg"
    render_meme(image_path, MEME["top"], MEME["bottom"], out)

    print("\nDone. Open the file to check it:")
    print(f"  {out}")


if __name__ == "__main__":
    main()
