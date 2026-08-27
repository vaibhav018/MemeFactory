#!/usr/bin/env python3
"""Find candidate clips for the Curated format, and pre-solve the mechanics.

Taste cannot be automated — which clip is worth posting is the whole value of
the format, and that is a human call. Everything around that call can be
automated, so this does all of it:

  * pulls recent Reels from the watchlist, ranked by engagement
  * downloads each one and detects the inner footage band, so a clip that is
    already somebody's finished vertical post with their own header baked in
    comes back with the crop that lifts out just the source
  * writes a preview frame of exactly what would be shown
  * emits a candidates.json with a ready-to-edit curated job per clip

Then a human looks at ten frames, picks one, and writes a line of commentary.

    python scripts/discover_reels.py [--days 14] [--top 10]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "discover"
ACTOR_URL = "https://api.apify.com/v2/acts/apify~instagram-scraper/run-sync-get-dataset-items"


def load_env() -> None:
    env = BASE / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def watchlist() -> list[str]:
    path = BASE / "config" / "handles_watchlist.yaml"
    if not path.exists():
        return ["evolving.ai", "stics.ai", "syntaix.ai", "askgpts"]
    import yaml
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    handles = data.get("handles", data) if isinstance(data, dict) else data
    out = []
    for h in handles:
        name = h.get("handle") if isinstance(h, dict) else h
        if name:
            out.append(str(name).lstrip("@"))
    return out


def detect_band(path: Path) -> tuple[dict | None, float]:
    """Find the inner footage band, and return (crop, source_aspect).

    Rows lit in EVERY sampled frame are the clip; rows that go dark somewhere
    are the poster's own letterbox and chrome. Sampling several frames is what
    makes this reliable — a single frame cannot tell a black bar from a dark
    shot.
    """
    import cv2
    import numpy as np

    cap = cv2.VideoCapture(str(path))
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    if not (n and w and h):
        cap.release()
        return None, 16 / 9

    rows = []
    for pct in (0.15, 0.28, 0.4, 0.5, 0.6, 0.72, 0.85):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(n * pct))
        ok, frame = cap.read()
        if ok:
            # Does this row carry ANY real content? Requiring most of the row
            # to be bright fails on dark cinematic footage — a night battle
            # scene never clears it, the band comes back empty, and the clip
            # gets waved through as "already raw" with the poster's header
            # still baked in.
            rows.append(frame.max(axis=2).max(axis=1) > 26)
    cap.release()
    if not rows:
        return None, w / h

    lit = np.logical_and.reduce(np.array(rows))
    idx = np.where(lit)[0]
    if len(idx) < 10:
        return None, w / h

    # Longest CONTIGUOUS run, not min..max. The poster's header has white text
    # in it, so its rows are lit in every frame too; spanning the extremes
    # swallows the header, the gap and the caption line in one band.
    best = run_a = a = int(idx[0])
    best_b = int(idx[0])
    for i in range(1, len(idx)):
        if idx[i] != idx[i - 1] + 1:
            if idx[i - 1] - a > best_b - best:
                best, best_b = a, int(idx[i - 1])
            a = int(idx[i])
    if idx[-1] - a > best_b - best:
        best, best_b = a, int(idx[-1])

    top, bot = best, best_b
    frac_h = (bot - top) / h
    # A band covering nearly the whole frame means the clip is already raw.
    if frac_h > 0.92:
        return None, w / h

    crop = {"top": round(top / h, 4), "height": round(frac_h, 4)}
    # Dark, letterboxed cinematic footage can lose this contest to the poster's
    # own header: the header is bright in every frame and unbroken, the film is
    # neither, so the longest contiguous lit run turns out to be the branding.
    # A real footage band is most of the frame. Anything this thin is a failed
    # detection, and cropping to it would publish somebody's logo full-bleed —
    # so it is marked rather than trusted, and the publishers refuse it.
    if frac_h < 0.25:
        crop["suspect"] = True
    return crop, w / h


def preview(path: Path, dest: Path, crop: dict | None) -> None:
    """Write a frame of what would actually appear, cropped as we would crop."""
    import cv2

    cap = cv2.VideoCapture(str(path))
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(n * 0.45))
    ok, frame = cap.read()
    cap.release()
    if not ok:
        return
    if crop:
        h = frame.shape[0]
        a = int(h * crop["top"])
        b = a + int(h * crop["height"])
        frame = frame[a:b]
    cv2.imwrite(str(dest), frame)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=14)
    ap.add_argument("--top", type=int, default=10, help="candidates to keep overall")
    ap.add_argument("--per-handle", type=int, default=18, help="posts to scan per handle")
    ap.add_argument("--handles", nargs="*", default=None)
    args = ap.parse_args()

    load_env()
    token = os.getenv("APIFY_TOKEN")
    if not token:
        sys.exit("APIFY_TOKEN not set")

    handles = args.handles or watchlist()
    cutoff = datetime.now(timezone.utc) - timedelta(days=args.days)
    OUT.mkdir(parents=True, exist_ok=True)

    pool = []
    for h in handles:
        print(f"-> @{h}")
        try:
            r = requests.post(ACTOR_URL, params={"token": token}, timeout=300, json={
                "directUrls": [f"https://www.instagram.com/{h}/"],
                "resultsType": "posts",
                "resultsLimit": args.per_handle,
                "addParentData": False,
            })
        except Exception as e:
            print(f"   failed: {e}")
            continue
        if not r.ok:
            print(f"   HTTP {r.status_code}")
            continue

        for p in r.json():
            if not isinstance(p, dict) or not p.get("videoUrl"):
                continue
            try:
                when = datetime.fromisoformat(str(p.get("timestamp")).replace("Z", "+00:00"))
            except Exception:
                when = None
            if when and when < cutoff:
                continue
            pool.append({
                "handle": h,
                "shortcode": p.get("shortCode"),
                "url": f"https://www.instagram.com/reel/{p.get('shortCode')}/",
                "videoUrl": p["videoUrl"],
                "engagement": (p.get("likesCount") or 0) + (p.get("commentsCount") or 0),
                "seconds": round(float(p.get("videoDuration") or 0), 1),
                "posted": when.isoformat()[:10] if when else "?",
                "caption": (p.get("caption") or "").replace("\n", " ")[:300],
            })
        time.sleep(1)

    pool.sort(key=lambda c: c["engagement"], reverse=True)
    print(f"\n{len(pool)} reels in the last {args.days} days; taking top {args.top}\n")

    kept = []
    for c in pool[:args.top]:
        mp4 = OUT / f"{c['shortcode']}.mp4"
        try:
            mp4.write_bytes(requests.get(c["videoUrl"], timeout=300).content)
        except Exception as e:
            print(f"   {c['shortcode']}: download failed {e}")
            continue

        crop, aspect = detect_band(mp4)
        preview(mp4, OUT / f"{c['shortcode']}.jpg", crop)
        mp4.unlink()          # keep previews, not gigabytes of video

        c["sourceAspect"] = round(aspect, 4)
        c["sourceCrop"] = crop
        c.pop("videoUrl")
        kept.append(c)
        tag = ("SUSPECT CROP - set it by hand" if (crop or {}).get("suspect")
               else "cropped" if crop else "already raw")
        print(f"  {c['engagement']:>7} | {c['seconds']:>5.1f}s | {c['posted']} | "
              f"@{c['handle'][:16]:<16} | {tag}")

    # A targeted probe (--handles one_account) writes the same file a full
    # sweep does, and a full sweep is 13 Apify calls and several minutes. Keep
    # the previous result so a narrow run cannot quietly destroy a wide one.
    out_file = OUT / "candidates.json"
    if out_file.exists():
        (OUT / "candidates.prev.json").write_text(
            out_file.read_text(encoding="utf-8"), encoding="utf-8")
    out_file.write_text(
        json.dumps(kept, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n{len(kept)} candidates -> {OUT}")
    print("Look at the .jpg previews, pick one, then write the commentary line.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
