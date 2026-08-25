"""Cut the background out of the presenter portrait — run once, commit result.

The source headshot sits on bright green outdoor bokeh, which fights the
black/yellow identity badly. This strips it to alpha so the Reel composition
can sit the subject on the brand ground.

Deliberately NOT part of the render path: the portrait is a static asset, and
running a segmentation model on every CI render would be minutes of waste per
reel. Run this locally when the portrait changes, commit reels/public/portrait.png,
and the pipeline just reads the file.

    python scripts/cutout_portrait.py <source-image> [--out reels/public/portrait.png]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
DEFAULT_OUT = BASE / "reels" / "public" / "portrait.png"
TARGET_W = 1080


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("source", help="Portrait image to cut out")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--width", type=int, default=TARGET_W,
                    help="Resize longest-fit width for the 1080-wide canvas")
    args = ap.parse_args()

    src = Path(args.source)
    if not src.exists():
        sys.stderr.write(f"no such file: {src}\n")
        return 2

    try:
        from rembg import remove, new_session
    except ImportError:
        sys.stderr.write(
            "rembg not installed. Run:\n"
            "    pip install --user rembg onnxruntime\n"
            "(first run downloads the u2net weights, ~176MB)\n"
        )
        return 3

    from PIL import Image

    img = Image.open(src).convert("RGBA")
    print(f"source      {img.width}x{img.height}")

    # u2net_human_seg is tuned for people and holds hair edges far better
    # than the generic model on a busy bokeh background.
    session = new_session("u2net_human_seg")
    cut = remove(img, session=session)

    # Trim fully transparent margins so the subject anchors predictably.
    bbox = cut.getbbox()
    if bbox:
        cut = cut.crop(bbox)
        print(f"trimmed     {cut.width}x{cut.height}")

    if cut.width != args.width:
        h = round(cut.height * args.width / cut.width)
        cut = cut.resize((args.width, h), Image.LANCZOS)
        print(f"resized     {cut.width}x{cut.height}")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    cut.save(out, format="PNG", optimize=True)
    print(f"wrote       {out}  ({out.stat().st_size // 1024} KB)")

    # A near-opaque result means segmentation failed and returned the frame.
    alpha = cut.getchannel("A")
    transparent = sum(1 for p in alpha.getdata() if p < 16)
    frac = transparent / (cut.width * cut.height)
    print(f"transparent {frac:.1%} of pixels")
    if frac < 0.05:
        sys.stderr.write("WARNING: almost nothing was removed — check the result.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
