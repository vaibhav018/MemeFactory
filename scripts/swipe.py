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
  python scripts/swipe.py --backend apify       # force Apify backend

Then feed the results into scripts/swipe_to_queue.py.

Two backends, selected by --backend or SWIPE_BACKEND env var:

  apify (recommended, ~$0.0015/post) — hits Apify's managed IG scraper
    actor. Zero rate-limit babysitting; they maintain endpoint changes.
    Set APIFY_TOKEN in .env. Free tier ships with $5 credit (~3300 posts).

  instaloader (free but fragile) — direct scraping via a cached burner
    IG session. See "Login mode" below. Anonymous access 429s instantly
    in 2026, so login is required for this backend.

The default is apify if APIFY_TOKEN is set, otherwise instaloader.

Login mode (Instaloader backend only — anonymous access gets 429'd
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
    instaloader = None  # only needed if backend=instaloader

import requests


BASE = Path(__file__).resolve().parents[1]
WATCHLIST_PATH = BASE / "config" / "handles_watchlist.yaml"
SWIPE_DIR = BASE / "swipe"

APIFY_ACTOR = "apify~instagram-scraper"
APIFY_RUN_SYNC_URL = f"https://api.apify.com/v2/acts/{APIFY_ACTOR}/run-sync-get-dataset-items"


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


def _download_image(url: str, dest: Path) -> bool:
    """Fetch an IG CDN image URL to dest. Returns True on success."""
    try:
        r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
    except requests.RequestException as e:
        print(f"    [warn] image download failed: {e}")
        return False
    dest.write_bytes(r.content)
    return True


def scrape_handle_apify(
    token: str,
    handle: str,
    top_n: int,
    days: int,
    fetch_multiplier: int = 3,
    image_dir: Path | None = None,
) -> dict | None:
    """Hit Apify's instagram-scraper actor synchronously. Returns None on error.

    Apify returns newest-first; we fetch top_n * fetch_multiplier so we have
    enough posts to filter to the last `days` window before ranking.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    payload = {
        "directUrls": [f"https://www.instagram.com/{handle}/"],
        "resultsType": "posts",
        "resultsLimit": max(top_n * fetch_multiplier, 12),
        "searchType": "user",
        "addParentData": False,
    }
    try:
        r = requests.post(
            APIFY_RUN_SYNC_URL,
            params={"token": token},
            json=payload,
            timeout=180,
        )
    except requests.RequestException as e:
        print(f"  [skip] @{handle} — request failed: {e}")
        return None
    if r.status_code == 404:
        print(f"  [skip] @{handle} — actor returned 404 (handle may not exist)")
        return None
    if r.status_code >= 400:
        print(f"  [skip] @{handle} — apify HTTP {r.status_code}: {r.text[:200]}")
        return None
    try:
        items = r.json()
    except Exception as e:
        print(f"  [skip] @{handle} — bad JSON: {e}")
        return None
    if not items:
        print(f"  [skip] @{handle} — 0 posts returned (private / non-existent / blocked)")
        return None

    posts = []
    for it in items:
        # Apify shape: shortCode, url, caption, likesCount, commentsCount,
        # timestamp (ISO), type ("Image"/"Video"/"Sidecar"), hashtags[],
        # displayUrl (cover image URL).
        ts = it.get("timestamp")
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00")) if ts else None
        except Exception:
            dt = None
        if dt and dt < cutoff:
            continue
        posts.append({
            "shortcode": it.get("shortCode") or it.get("id") or "",
            "url": it.get("url") or f"https://www.instagram.com/p/{it.get('shortCode','')}/",
            "date_utc": (dt or datetime.now(timezone.utc)).isoformat(),
            "likes": it.get("likesCount") or 0,
            "comments": it.get("commentsCount") or 0,
            "engagement": (it.get("likesCount") or 0) + (it.get("commentsCount") or 0),
            "is_video": (it.get("type") == "Video"),
            "typename": it.get("type") or "",
            "caption": (it.get("caption") or "").strip(),
            "hashtags": it.get("hashtags") or [],
            "display_url": it.get("displayUrl") or "",
        })

    posts.sort(key=lambda p: p["engagement"], reverse=True)
    top = posts[:top_n]

    # Download cover images for the top posts only — cheaper and enough for
    # slide-1 covers. Multi-image carousels: we take the first image (cover).
    if image_dir is not None:
        image_dir.mkdir(parents=True, exist_ok=True)
        for p in top:
            url = p.get("display_url")
            if not url or not p["shortcode"]:
                continue
            dest = image_dir / f"{p['shortcode']}.jpg"
            if dest.exists() and dest.stat().st_size > 0:
                p["image_path"] = str(dest.relative_to(BASE))
                continue
            if _download_image(url, dest):
                p["image_path"] = str(dest.relative_to(BASE))
                print(f"    ↓ cover: {dest.name} ({dest.stat().st_size // 1024}KB)")

    return {
        "handle": handle,
        "backend": "apify",
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "window_days": days,
        "posts_seen": len(posts),
        "top": top,
    }


def scrape_handle(
    loader: "instaloader.Instaloader",
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


def _pick_backend(cli_choice: str | None) -> str:
    if cli_choice:
        return cli_choice
    env = os.getenv("SWIPE_BACKEND", "").strip().lower()
    if env in ("apify", "instaloader"):
        return env
    # Auto: Apify if token exists, else fall back to instaloader.
    return "apify" if os.getenv("APIFY_TOKEN") else "instaloader"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--handle", help="Scrape only this handle")
    ap.add_argument("--top", type=int, default=10, help="Top N per handle (default 10)")
    ap.add_argument("--days", type=int, default=30, help="Lookback window (default 30)")
    ap.add_argument("--sleep", type=float, default=8.0,
                    help="Seconds between handles (instaloader only; default 8)")
    ap.add_argument("--backend", choices=["apify", "instaloader"],
                    help="Override auto-detect (apify if APIFY_TOKEN set, else instaloader)")
    ap.add_argument("--no-images", dest="download_images", action="store_false",
                    default=True, help="Skip cover-image download (apify backend only)")
    args = ap.parse_args()

    handles = load_handles(only=args.handle)
    SWIPE_DIR.mkdir(exist_ok=True)

    backend = _pick_backend(args.backend)
    print(f"→ backend: {backend}")

    loader = None
    apify_token = ""
    if backend == "apify":
        apify_token = os.getenv("APIFY_TOKEN", "").strip()
        if not apify_token:
            sys.stderr.write("APIFY_TOKEN not set in .env. Aborting.\n")
            return 2
    else:
        if instaloader is None:
            sys.stderr.write("instaloader not installed. `pip install instaloader`.\n")
            return 2
        loader = build_loader()

    print(f"Scraping {len(handles)} handle(s) — top {args.top}, last {args.days}d")
    ok = 0
    for i, entry in enumerate(handles):
        h = entry["handle"]
        print(f"→ @{h}  ({', '.join(entry.get('pillar_affinity') or []) or 'no-pillar'})")
        out_dir = SWIPE_DIR / h
        out_dir.mkdir(parents=True, exist_ok=True)
        if backend == "apify":
            result = scrape_handle_apify(
                apify_token, h, args.top, args.days,
                image_dir=out_dir if args.download_images else None,
            )
        else:
            result = scrape_handle(loader, h, args.top, args.days)
        if result is None:
            continue
        result["pillar_affinity"] = entry.get("pillar_affinity") or []
        result["why"] = (entry.get("why") or "").strip()
        (out_dir / "latest.json").write_text(json.dumps(result, indent=2, ensure_ascii=False))
        print(f"   kept {len(result['top'])} of {result['posts_seen']} seen")
        ok += 1
        # Only sleep between calls on instaloader — Apify handles its own throttling.
        if backend == "instaloader" and i < len(handles) - 1 and args.sleep > 0:
            time.sleep(args.sleep)

    print(f"\nDone. {ok}/{len(handles)} handles scraped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
