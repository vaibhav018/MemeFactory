"""Telegram channel scraper — runs on Termux, feeds the GitHub Actions pipeline.

Reads recent messages from Telugu news Telegram channels and writes
data/telegram_cache.json in the same NewsItem format used by news_scraper.py.
GitHub Actions picks it up automatically on the next scheduled run.

Setup (one-time):
  pkg install python nodejs
  pip install telethon python-dotenv
  Get API credentials at https://my.telegram.org/apps  (free, instant)
  Add to .env in this repo:
    TELEGRAM_API_ID=12345678
    TELEGRAM_API_HASH=abcdef1234567890abcdef1234567890

First run will prompt you to log in with your phone number (OTP). After that
the session is saved to .telegram_session.session and re-used silently.

Usage:
  python telegram_scraper.py                # last 12 hours, no push
  python telegram_scraper.py --hours 6      # last 6 hours
  python telegram_scraper.py --push         # write cache + git push to trigger pipeline

Cron on Termux (run every 2 hours):
  crontab -e
  0 */2 * * * cd ~/MemeFactory && python telegram_scraper.py --hours 3 --push >> output/logs/telegram.log 2>&1
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from telethon import TelegramClient
    from telethon.tl.types import Message
except ImportError:
    raise SystemExit("telethon not installed. Run: pip install telethon")

_REPO = Path(__file__).parent
SESSION_FILE = _REPO / ".telegram_session"
OUTPUT_FILE = _REPO / "data" / "telegram_cache.json"

CHANNELS = [
    {"username": "tv9telugu",        "name": "TV9 Telugu",        "language": "te"},
    {"username": "sakshitv",         "name": "Sakshi TV",         "language": "te"},
    {"username": "ntv_telugu",       "name": "NTV Telugu",        "language": "te"},
    {"username": "bbctelugu",        "name": "BBC Telugu",        "language": "te"},
    {"username": "abnnews",          "name": "ABN Andhra Jyothi", "language": "te"},
    {"username": "etvbharat_te",     "name": "ETV Bharat Telugu", "language": "te"},
    {"username": "eenadu_telugu",    "name": "Eenadu",            "language": "te"},
]

# Minimum message length to bother including (filters out stickers, emojis-only, etc.)
_MIN_MSG_LEN = 25


def _split_title_desc(text: str) -> tuple[str, str]:
    """First line = title, rest = description (common Telegram news post format)."""
    lines = [ln.strip() for ln in text.strip().split("\n") if ln.strip()]
    if not lines:
        return "", ""
    return lines[0], " ".join(lines[1:]) if len(lines) > 1 else ""


async def _scrape_channel(
    client: TelegramClient, ch: dict, since: datetime, limit: int = 100
) -> list[dict]:
    items: list[dict] = []
    try:
        entity = await client.get_entity(ch["username"])
        async for msg in client.iter_messages(entity, limit=limit):
            if not isinstance(msg, Message) or not msg.text:
                continue
            msg_date = msg.date if msg.date.tzinfo else msg.date.replace(tzinfo=timezone.utc)
            if msg_date < since:
                break
            text = " ".join(msg.text.split())  # collapse whitespace
            if len(text) < _MIN_MSG_LEN:
                continue
            title, description = _split_title_desc(msg.text)
            items.append({
                "title": title,
                "description": description,
                "url": f"https://t.me/{ch['username']}/{msg.id}",
                "source": ch["name"],
                "published_at": msg_date.isoformat(),
                "language": ch["language"],
                "matched_keywords": [],
                "score": 0.0,
                "source_type": "telegram",
            })
        print(f"  {ch['name']}: {len(items)} messages")
    except Exception as exc:
        print(f"  !! {ch['name']} skipped: {exc}")
    return items


async def _run(hours: int, push: bool) -> None:
    api_id = os.getenv("TELEGRAM_API_ID")
    api_hash = os.getenv("TELEGRAM_API_HASH")
    if not api_id or not api_hash:
        raise SystemExit(
            "TELEGRAM_API_ID / TELEGRAM_API_HASH not set.\n"
            "Get them free at https://my.telegram.org/apps and add to .env"
        )

    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    print(f"Fetching Telegram messages since {since.strftime('%Y-%m-%d %H:%M UTC')} ({hours}h window)\n")

    client = TelegramClient(str(SESSION_FILE), int(api_id), api_hash)
    await client.start()

    all_items: list[dict] = []
    for ch in CHANNELS:
        items = await _scrape_channel(client, ch, since)
        all_items.extend(items)

    await client.disconnect()

    all_items.sort(key=lambda x: x["published_at"], reverse=True)

    OUTPUT_FILE.parent.mkdir(exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_items, f, ensure_ascii=False, indent=2)
    print(f"\nWrote {len(all_items)} items -> {OUTPUT_FILE}")

    if push:
        _git_push()


def _git_push() -> None:
    stamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ")
    cmds = [
        ["git", "-C", str(_REPO), "add", "data/telegram_cache.json"],
        ["git", "-C", str(_REPO), "commit", "-m", f"telegram cache {stamp}"],
        ["git", "-C", str(_REPO), "push"],
    ]
    for cmd in cmds:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            # "nothing to commit" is fine
            if "nothing to commit" in result.stdout + result.stderr:
                print("Nothing new to push.")
                return
            print(f"!! {' '.join(cmd)} failed:\n{result.stderr.strip()}")
            return
    print("Pushed telegram_cache.json to GitHub — pipeline will pick it up on next run.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape Telugu Telegram news channels")
    parser.add_argument("--hours", type=int, default=12, help="Fetch messages from last N hours (default: 12)")
    parser.add_argument("--push", action="store_true", help="Git push telegram_cache.json after writing")
    args = parser.parse_args()
    asyncio.run(_run(args.hours, args.push))


if __name__ == "__main__":
    main()
