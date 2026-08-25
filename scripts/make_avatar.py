#!/usr/bin/env python3
"""Build the small circular avatar used in the curated-video header.

Crops the head out of the cutout portrait and masks it to a circle. Run once
and commit the result — like the cutout itself, this is a static asset and has
no business running on every render.

    python scripts/make_avatar.py [--size 256]
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw

BASE = Path(__file__).resolve().parents[1]
SRC = BASE / "reels" / "public" / "portrait.png"
OUT = BASE / "reels" / "public" / "avatar.png"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", type=int, default=256)
    ap.add_argument("--source", default=str(SRC))
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    src = Path(args.source)
    if not src.exists():
        raise SystemExit(f"no portrait at {src} — run scripts/cutout_portrait.py first")

    img = Image.open(src).convert("RGBA")

    # The cutout is trimmed to the subject, so the head sits at the top. Take a
    # square from the upper region rather than centre-cropping, which would
    # frame the chest.
    side = int(img.width * 0.62)
    left = (img.width - side) // 2
    top = int(img.height * 0.02)
    head = img.crop((left, top, left + side, top + side))
    head = head.resize((args.size, args.size), Image.LANCZOS)

    # Flatten onto the brand ground first: a circular mask over transparency
    # leaves ragged edges wherever the cutout was already soft.
    bg = Image.new("RGBA", head.size, (20, 20, 24, 255))
    bg.alpha_composite(head)

    mask = Image.new("L", (args.size * 4, args.size * 4), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, args.size * 4, args.size * 4), fill=255)
    mask = mask.resize(head.size, Image.LANCZOS)   # supersampled = smooth edge

    out = Image.new("RGBA", head.size, (0, 0, 0, 0))
    out.paste(bg, (0, 0), mask)

    dest = Path(args.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    out.save(dest, format="PNG", optimize=True)
    print(f"wrote {dest}  {out.width}x{out.height}  {dest.stat().st_size // 1024} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
