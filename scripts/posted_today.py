#!/usr/bin/env python3
"""Has today's post for a given slot already gone out?

GitHub's cron is best-effort. This account's 05:30 UTC carousel slot has been
firing 23-31 minutes late every day, and on 27 Aug 2026 it did not fire at
all — no run, no failure, nothing to notice. The fix is to schedule catch-up
attempts and let each one ask Instagram whether the work is already done, so a
dropped trigger costs a delay instead of a missed day.

    python scripts/posted_today.py --kind reel       # exit 0 = already posted
    python scripts/posted_today.py --kind carousel   # exit 1 = still owed

Exit 1 also covers "could not tell" (no token, API error). Publishing twice is
recoverable; skipping a day because a health check flaked is not.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

BASE = Path(__file__).resolve().parents[1]
IST = timezone(timedelta(hours=5, minutes=30))

# me/media is ordered newest first; a day's worth of posts is a handful.
API = "https://graph.instagram.com/v21.0/me/media"

KINDS = {
    "reel": lambda m: m.get("media_product_type") == "REELS",
    "carousel": lambda m: m.get("media_product_type") == "FEED",
}


def load_env() -> None:
    env = BASE / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", choices=sorted(KINDS), required=True)
    args = ap.parse_args()

    load_env()
    token = os.getenv("IG_ACCESS_TOKEN")
    if not token:
        print("IG_ACCESS_TOKEN not set — treating the slot as unposted")
        return 1

    try:
        r = requests.get(API, timeout=60, params={
            "fields": "id,media_type,media_product_type,timestamp,permalink",
            "limit": 15, "access_token": token})
        data = r.json()
    except Exception as e:
        print(f"media lookup failed ({e}) — treating the slot as unposted")
        return 1

    if "data" not in data:
        print(f"media lookup returned no data ({data.get('error')}) — "
              f"treating the slot as unposted")
        return 1

    today = datetime.now(IST).date()
    matches = KINDS[args.kind]
    for m in data["data"]:
        try:
            when = datetime.fromisoformat(m["timestamp"].replace("Z", "+00:00"))
        except Exception:
            continue
        if when.astimezone(IST).date() == today and matches(m):
            print(f"{args.kind} already posted today at "
                  f"{when.astimezone(IST):%H:%M IST} — {m['permalink']}")
            return 0

    print(f"no {args.kind} posted yet today ({today})")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
