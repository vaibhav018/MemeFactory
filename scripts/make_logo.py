#!/usr/bin/env python3
"""Generate the circular brand logo used as the account avatar in headers.

Replaces the operator portrait, which is not used anywhere in this pipeline.
Run once and commit; it is a static asset.

    python scripts/make_logo.py [--size 256]
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BASE = Path(__file__).resolve().parents[1]
FONT = BASE / "assets" / "fonts" / "Anton-Regular.ttf"
OUT = BASE / "reels" / "public" / "logo.png"

INK = (11, 11, 12, 255)
ACCENT = (255, 222, 0, 255)
PAPER = (255, 255, 255, 255)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", type=int, default=512)
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    S = args.size
    SS = 4                      # supersample, for a clean circular edge
    W = S * SS

    img = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Solid brand ground, then a yellow ring inset from the edge. The ring is
    # what reads at 92px in the reel header — a flat disc disappears on black.
    d.ellipse((0, 0, W, W), fill=INK)
    ring = int(W * 0.055)
    d.ellipse((ring // 2, ring // 2, W - ring // 2, W - ring // 2),
              outline=ACCENT, width=ring)

    # Monogram. Anton is the display face used across every slide, so the mark
    # is consistent with the type rather than being a separate identity.
    if FONT.exists():
        font = ImageFont.truetype(str(FONT), int(W * 0.46))
    else:
        font = ImageFont.load_default()

    text = "PP"
    box = d.textbbox((0, 0), text, font=font)
    tw, th = box[2] - box[0], box[3] - box[1]
    d.text(((W - tw) / 2 - box[0], (W - th) / 2 - box[1] - W * 0.015),
           text, font=font, fill=PAPER)

    # A yellow underscore below the monogram, echoing the handle's trailing _.
    bar_w, bar_h = int(W * 0.30), int(W * 0.045)
    bx, by = (W - bar_w) // 2, int(W * 0.70)
    d.rectangle((bx, by, bx + bar_w, by + bar_h), fill=ACCENT)

    # Mask to a circle at supersampled size, then downsample once.
    mask = Image.new("L", (W, W), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, W, W), fill=255)
    out = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    out = out.resize((S, S), Image.LANCZOS)

    dest = Path(args.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    out.save(dest, format="PNG", optimize=True)
    print(f"wrote {dest}  {out.width}x{out.height}  {dest.stat().st_size // 1024} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
