"""
Swipe-file scraper — pulls top-engaging posts from competitor IG handles
into swipe/<handle>/latest.json for the copy-cat content pipeline.

Ranks by (likes + comments) across posts from the last --days window and
keeps the top --top per handle. Skips handles that don't exist or are
private — logs a warning and moves on. Never crashes the whole run.

Usage:
  python scripts/swipe.py                       # scrape all handles
  python scripts/swipe.py --handle wealthpill_  # scrape one handle
  python scripts/swipe.py --top 15 --days 45    # custom ranking window

Then feed the results into scripts/swipe_to_queue.py.

Rate-limiting: uses Instaloader's default request throttle (~1 request /
~1.5 sec) which is safe for public data on a residential IP. Do NOT run
this from the GitHub Actions runner — datacenter IPs get 429'd quickly.
Run it from Termux on your phone (residential IP) instead.

Login mode (STRONGLY recommended in 2026 — anonymous access gets 429'd
almost immediately):

  1. Create a burner Instagram account via the actual IG app on your
     phone (not via Instaloader). Verify email/phone. Follow ~30-50
     random accounts so it looks legit. Wait 24h before first scrape.

  2. One-time interactive login (saves an encrypted session file
     under ~/.config/instaloader/ so we never re-authenticate):

        instaloader --login=<burner_username>

     Enter password when prompted. Done — session is now cached.

  3. Add to MemeFactory/.env:

        IG_SWIPE_USER=<burner_username>

     (No password — swipe.py loads the saved session.)

  4. Run scripts/swipe.py. It picks up the env var, loads the session,
     and hits IG's endpoints as your burner account. If the burner ever
     gets soft-banned, create a new one — nothing else changes.

Between-handle sleep (--sleep, default 8s) is added on top of Instaloader's
internal throttle to keep the burner account under the radar.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")
except ImportError:
    pass  # dotenv is optional — env vars from shell still work.

try:
    import instaloader
except ImportError:
    sys.stderr.write(
        "instaloader not installed. Run: pip install -r requirements.txt\n"
    )
    sys.exit(1)


BASE = Path(__file__).resolve().parents[1]
WATCHLIST_PATH = BASE / "config" / "handles_watchlist.yaml"
SWIPE_DIR = BASE / "swipe"


def load_handles(only: str | None = None) -> list[dict]:
    with WATCHLIST_PATH.open() as f:
        data = yaml.safe_load(f)
    entries = [
        h for h in data.get("handles", [])
        if h.get("platform", "instagram") == "instagram"
    ]
    if only:
        entries = [h for h in entries if h["handle"] == only]
        if not entries:
            sys.stderr.write(f"Handle {only!r} not in watchlist.\n")
            sys.exit(1)
    return entries


def scrape_handle(
    loader: instaloader.Instaloader,
    handle: str,
    top_n: int,
    days: int,
) -> dict | None:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    try:
        profile = instaloader.Profile.from_username(loader.context, handle)
    except instaloader.exceptions.ProfileNotExistsException:
        print(f"  [skip] @{handle} — profile does not exist")
        return None
    except instaloader.exceptions.PrivateProfileNotFollowedException:
        print(f"  [skip] @{handle} — private profile")
        return None
    except Exception as e:
        print(f"  [skip] @{handle} — {type(e).__name__}: {e}")
        return None

    posts = []
    for i, post in enumerate(profile.get_posts()):
        # get_posts() is newest-first; stop once we're past the window.
        if post.date_utc.replace(tzinfo=timezone.utc) < cutoff:
            # Look a bit further in case the feed has pinned posts, then break.
            if i > 6:
                break
            continue
        posts.append({
            "shortcode": post.shortcode,
            "url": f"https://www.instagram.com/p/{post.shortcode}/",
            "date_utc": post.date_utc.isoformat(),
            "likes": post.likes,
            "comments": post.comments,
            "engagement": (post.likes or 0) + (post.comments or 0),
            "is_video": post.is_video,
            "typename": post.typename,
            "caption": (post.caption or "").strip(),
            "hashtags": list(post.caption_hashtags or []),
        })
        # Tiny extra sleep to be polite on top of Instaloader's internal throttle.
        time.sleep(0.4)

    posts.sort(key=lambda p: p["engagement"], reverse=True)
    top = posts[:top_n]
    return {
        "handle": handle,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "window_days": days,
        "posts_seen": len(posts),
        "top": top,
    }


def build_loader() -> instaloader.Instaloader:
    """Build a loader, using the cached burner session if IG_SWIPE_USER is set."""
    loader = instaloader.Instaloader(
        download_pictures=False,
        download_videos=False,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
        compress_json=False,
        quiet=True,
    )
    user = os.getenv("IG_SWIPE_USER", "").strip()
    if user:
        try:
            loader.load_session_from_file(user)
            print(f"→ logged in as @{user} (cached session)")
        except FileNotFoundError:
            sys.stderr.write(
                f"\n✗ No cached session for @{user}. Run once interactively:\n"
                f"    instaloader --login={user}\n"
                f"(enter password when prompted). This saves the session and\n"
                f"future runs won't need to re-authenticate.\n\n"
            )
            sys.exit(2)
    else:
        print("→ ⚠ anonymous mode — will 429 quickly. Set IG_SWIPE_USER for login mode.")
    return loader


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--handle", help="Scrape only this handle")
    ap.add_argument("--top", type=int, default=10, help="Top N per handle (default 10)")
    ap.add_argument("--days", type=int, default=30, help="Lookback window (default 30)")
    ap.add_argument("--sleep", type=float, default=8.0,
                    help="Seconds between handles to stay under IG's radar (default 8)")
    args = ap.parse_args()

    handles = load_handles(only=args.handle)
    SWIPE_DIR.mkdir(exist_ok=True)

    loader = build_loader()

    print(f"Scraping {len(handles)} handle(s) — top {args.top}, last {args.days}d")
    ok = 0
    for i, entry in enumerate(handles):
        h = entry["handle"]
        print(f"→ @{h}  ({', '.join(entry.get('pillar_affinity') or []) or 'no-pillar'})")
        result = scrape_handle(loader, h, args.top, args.days)
        if result is None:
            continue
        result["pillar_affinity"] = entry.get("pillar_affinity") or []
        result["why"] = (entry.get("why") or "").strip()
        out_dir = SWIPE_DIR / h
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "latest.json").write_text(json.dumps(result, indent=2, ensure_ascii=False))
        print(f"   kept {len(result['top'])} of {result['posts_seen']} seen")
        ok += 1
        if i < len(handles) - 1 and args.sleep > 0:
            time.sleep(args.sleep)

    print(f"\nDone. {ok}/{len(handles)} handles scraped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
