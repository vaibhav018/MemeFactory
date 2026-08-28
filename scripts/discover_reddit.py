#!/usr/bin/env python3
"""Find candidate clips at the source instead of one repost downstream.

The Instagram sweep pulls from aggregators. This pulls from where they pull:
r/aivideo is where the Red Alert 2 film surfaced on 21 August, the same day
@evolving.ai reposted it and five days before we did.

Three deliberate choices, each checked rather than assumed:

  * **Discovery is Reddit's RSS**, not the API and not a scraper. Reddit's
    public JSON is 403 to unauthenticated clients, and self-service API
    registration closed in late 2025 — a new OAuth client now waits on manual
    approval that may never come, and the free tier is non-commercial anyway.
    The .rss endpoints still answer 200 unauthenticated. They rate-limit hard,
    hence the pacing below.
  * **Metadata and download are yt-dlp.** Reddit video is DASH with audio and
    video as separate streams; yt-dlp muxes them correctly and returns the
    score, comment count and author in the same call. Apify can do this too and
    costs credits per run to arrive at the same numbers.
  * **Nothing is selected automatically.** Score ranks the list; a person picks
    from preview frames. Reddit score measures what Reddit likes, which is not
    the same audience.

    python scripts/discover_reddit.py [--subs aivideo] [--top week] [--keep 12]
    python scripts/discover_reddit.py --fetch <post-url>
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import requests

# Reddit titles are full of emoji and non-Latin script, and the Windows console
# is cp1252 by default — printing one crashes the sweep after the network work
# is already paid for.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "discover"
VIDEO = BASE / "reels" / "public" / "video"
NS = {"a": "http://www.w3.org/2005/Atom"}
UA = "Mozilla/5.0 (compatible; profit-prompts/1.0)"

# The feed 429s on a second immediate request, so every network call waits.
PACE = 4.0


def feed(sub: str, top: str, limit: int) -> list[dict]:
    url = f"https://www.reddit.com/r/{sub}/top/.rss?t={top}&limit={limit}"
    r = requests.get(url, headers={"User-Agent": UA}, timeout=60)
    if r.status_code == 429:
        print(f"  r/{sub}: rate limited — wait a minute and retry")
        return []
    if not r.ok:
        print(f"  r/{sub}: HTTP {r.status_code}")
        return []
    out = []
    for e in ET.fromstring(r.content).findall("a:entry", NS):
        author = e.find("a:author/a:name", NS)
        out.append({
            "sub": sub,
            "title": (e.find("a:title", NS).text or "").strip(),
            "author": (author.text if author is not None else "").lstrip("/u/"),
            "url": e.find("a:link", NS).get("href"),
            "posted": (e.find("a:updated", NS).text or "")[:10],
        })
    return out


def probe(url: str) -> dict | None:
    """Score, duration and dimensions, without downloading the video."""
    import yt_dlp
    opts = {"quiet": True, "no_warnings": True, "noprogress": True,
            "skip_download": True, "http_headers": {"User-Agent": UA}}
    try:
        with yt_dlp.YoutubeDL(opts) as y:
            info = y.extract_info(url, download=False)
    except Exception as e:
        print(f"    probe failed: {str(e)[:90]}")
        return None
    if not info or not info.get("duration"):
        return None          # text post, image, or gallery
    return {
        "score": info.get("like_count") or 0,
        "comments": info.get("comment_count") or 0,
        "seconds": round(float(info["duration"]), 1),
        "width": info.get("width") or 0,
        "height": info.get("height") or 0,
    }


def download(url: str, dest: Path, cap: int = 0) -> bool:
    """Fetch a post's video. `cap` limits height — a preview does not need 4K.

    Without a cap this pulled 149MB to produce a 100KB preview frame. The
    publish copy is fetched separately at full quality by --fetch.
    """
    import yt_dlp
    dest.parent.mkdir(parents=True, exist_ok=True)
    fmt = (f"bestvideo[height<={cap}]+bestaudio/best[height<={cap}]/best"
           if cap else "bestvideo+bestaudio/best")
    opts = {"quiet": True, "no_warnings": True, "noprogress": True,
            "outtmpl": str(dest), "format": fmt, "merge_output_format": "mp4",
            "http_headers": {"User-Agent": UA}}
    try:
        with yt_dlp.YoutubeDL(opts) as y:
            y.download([url])
    except Exception as e:
        print(f"    download failed: {str(e)[:90]}")
        return False
    return dest.exists()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--subs", nargs="*", default=["aivideo"])
    ap.add_argument("--top", default="week", choices=["day", "week", "month"])
    ap.add_argument("--limit", type=int, default=25, help="posts to read per sub")
    ap.add_argument("--keep", type=int, default=12, help="candidates to download")
    ap.add_argument("--min-seconds", type=float, default=8.0)
    ap.add_argument("--fetch", default="", help="download one post url into reels/public/video")
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)

    if args.fetch:
        import yt_dlp
        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True,
                               "skip_download": True}) as y:
            info = y.extract_info(args.fetch, download=False)
        dest = VIDEO / f"rd_{info['id']}.mp4"
        if dest.exists():
            print(f"have {dest.name}")
            return 0
        if not download(args.fetch, dest):
            return 1
        print(f"fetched {dest.name} ({dest.stat().st_size // 1024} KB)")
        print(f'  videoSrc: "video/{dest.name}"')
        print(f'  credit:   u/{info.get("uploader")} — {args.fetch}')
        return 0

    posts = []
    for sub in args.subs:
        print(f"-> r/{sub}")
        posts += feed(sub, args.top, args.limit)
        time.sleep(PACE)
    if not posts:
        sys.exit("no posts — the feed is rate limiting; wait a minute")

    print(f"\n{len(posts)} posts; probing for video and score\n")
    vids = []
    for p in posts:
        meta = probe(p["url"])
        time.sleep(PACE)
        if not meta or meta["seconds"] < args.min_seconds:
            continue
        vids.append({**p, **meta})
        print(f"  {meta['score']:>6} | {meta['seconds']:>6.1f}s | u/{p['author'][:18]:<18} "
              f"{p['title'][:40]}")

    vids.sort(key=lambda c: c["score"], reverse=True)
    print(f"\n{len(vids)} video posts; downloading top {args.keep} for preview\n")

    sys.path.insert(0, str(BASE / "scripts"))
    from discover_reels import detect_band, preview

    kept = []
    for c in vids[:args.keep]:
        slug = c["url"].rstrip("/").split("/")[-2]
        shot = OUT / f"rd_{slug}.jpg"
        if shot.exists():
            print(f"  {c['score']:>6} | have preview | {c['title'][:44]}")
            c["sourceAspect"], c["sourceCrop"], c["permission"] = 0.0, None, "not_asked"
            kept.append(c)
            continue
        tmp = OUT / f"rd_{slug}.mp4"
        if not download(c["url"], tmp, cap=720):
            continue
        crop, aspect = detect_band(tmp)
        preview(tmp, shot, crop)
        tmp.unlink()
        c["sourceAspect"] = round(aspect, 4)
        c["sourceCrop"] = crop
        # Reddit posts are usually the creator's own, so crediting is exact and
        # asking costs one comment. That is worth tracking rather than assuming:
        # publish_reel refuses "denied" and warns on anything not granted.
        c["permission"] = "not_asked"
        kept.append(c)
        tag = ("SUSPECT" if (crop or {}).get("suspect")
               else "raw" if crop is None else "cropped")
        print(f"  {c['score']:>6} | {tag:<8} | {c['title'][:46]}")
        time.sleep(PACE)

    (OUT / "reddit_candidates.json").write_text(
        json.dumps(kept, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n{len(kept)} candidates -> {OUT / 'reddit_candidates.json'}")
    print("Look at the rd_*.jpg previews, pick one, then:")
    print("  python scripts/discover_reddit.py --fetch <url>")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
