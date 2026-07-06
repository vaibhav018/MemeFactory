#!/usr/bin/env python3
"""
AUTO MEME - the scheduled pipeline for @bhogeswar_rao_garu
==========================================================
One run = one meme:
  1. Scrape trending headlines from Google News RSS (no API key needed)
  2. Pick the freshest unused headline (Tollywood first)
  3. Download a related news photo (DuckDuckGo image search)
  4. Render it in the page's news-card format (meme_factory.py) with the
     Bhogeswar Rao garu watermark
  5. Remember the headline so it's never reused

Runs at 8AM / 1PM / 9PM via Windows Task Scheduler (see run_meme_bot.bat).
Run manually anytime:  python auto_meme.py

NOTE: pure content only - the headline is the entire caption (user's call:
no canned punchlines/clutter). A bottom bar renders only when a meme
explicitly supplies real content lines (see meme_factory.MEME for manual use).

This supersedes the older scheduler.py/news_scraper.py pipeline (built for
the old reaction-image format; never activated - its deps aren't installed).
"""

import json
import random
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

import requests

# reuse the renderer + image fetcher from meme_factory
from meme_factory import (DOWNLOAD_DIR, OUTPUT_DIR, REACTION_DIR, WHITE,
                          YELLOW, fetch_news_image, render_meme)

BASE = Path(__file__).resolve().parent      # portable: repo root, any OS
DATA_DIR = BASE / "data"
DATA_DIR.mkdir(exist_ok=True)
USED_FILE = DATA_DIR / "used_headlines.json"
LAST_MEME_FILE = DATA_DIR / "last_meme.json"

# ---------------------------------------------------------------- news feed
# category -> Google News RSS search query (en-IN edition), in posting priority
FEEDS = [
    ("tollywood", "Tollywood OR \"Telugu cinema\" box office OR movie"),
    ("andhra_telangana", "Telangana OR \"Andhra Pradesh\""),
    ("cricket", "India cricket"),
    ("national", "India viral trending"),
]
RSS_URL = "https://news.google.com/rss/search?q={q}&hl=en-IN&gl=IN&ceid=IN:en"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def clean_title(title: str) -> str:
    """Strip the ' - Source Name' suffix and truncated trailing fragments."""
    title = re.sub(r"\s+-\s+[^-]+$", "", title).strip()
    # Google News cuts long titles mid-clause; drop the dangling piece
    if ";" in title:
        title = title.split(";")[0].strip()
    return title


def fetch_headlines() -> list[dict]:
    items = []
    for category, query in FEEDS:
        url = RSS_URL.format(q=requests.utils.quote(query))
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            root = ET.fromstring(resp.content)
        except Exception as e:
            print(f"!! {category}: feed failed ({e})")
            continue
        count = 0
        for item in root.iter("item"):
            title = clean_title(item.findtext("title", ""))
            if not title or len(title) < 25 or len(title) > 160:
                continue
            items.append({"category": category, "headline": title})
            count += 1
            if count >= 8:
                break
        print(f">> {category}: {count} headlines")
    return items


def load_used() -> list:
    if USED_FILE.exists():
        return json.loads(USED_FILE.read_text(encoding="utf-8"))
    return []


def mark_used(headline: str):
    used = load_used()
    used.append(headline)
    USED_FILE.write_text(json.dumps(used[-500:], ensure_ascii=False, indent=1),
                         encoding="utf-8")


def pick_headline(items: list[dict]) -> dict | None:
    used = set(load_used())
    for item in items:                       # items are already in category priority
        if item["headline"] not in used:
            return item
    return None


# ---------------------------------------------------------------- image query
FILLER = re.compile(
    r"(box office collection|box office|collection|day \d+|review|"
    r"live updates?|breaking|latest news|highlights)", re.I)
STOPWORDS = {"the", "this", "that", "with", "from", "over", "after", "before",
             "india", "indian", "news", "when", "what", "how", "why"}

CATEGORY_SUFFIX = {
    "tollywood": "Telugu movie",
    "andhra_telangana": "Telangana Andhra news",
    "cricket": "India cricket match",
    "national": "India",
}


def extract_image_query(story: dict) -> tuple[str, str | None]:
    """Distill the headline into a focused image query + a relevance keyword.

    'Nagabandham Box Office Collection Day 1: Registers ...' ->
    ('Nagabandham Telugu movie', 'Nagabandham')
    """
    subject = re.split(r"[:\-–|]", story["headline"])[0]
    subject = FILLER.sub(" ", subject)
    subject = re.sub(r"[^\w\s']", " ", subject)
    words = subject.split()[:6]
    subject = " ".join(words).strip()
    if not subject:
        subject = " ".join(story["headline"].split()[:6])

    # relevance keyword: first distinctive word (likely the name/subject)
    keyword = next((w for w in words if len(w) > 3 and w.lower() not in STOPWORDS),
                   None)

    query = f"{subject} {CATEGORY_SUFFIX[story['category']]}"
    return query, keyword


# ---------------------------------------------------------------- captions
def make_captions(story: dict):
    """Pure content, no filler: headline only (white, top), no bottom bar."""
    top = [(story["headline"], WHITE)]
    bottom = []
    return top, bottom


# ---------------------------------------------------------------- main
def main():
    print("=" * 70)
    print(f"AUTO MEME run @ {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 70)

    items = fetch_headlines()
    if not items:
        sys.exit("!! No headlines fetched - aborting this run.")

    story = pick_headline(items)
    if story is None:
        sys.exit("!! All fetched headlines already used - aborting this run.")
    print(f">> Picked [{story['category']}]: {story['headline']}")

    query, keyword = extract_image_query(story)
    image_path = fetch_news_image(query, DOWNLOAD_DIR, must_contain=keyword)
    if image_path is None:
        print("!! No news photo found, falling back to a reaction image")
        candidates = list(REACTION_DIR.glob("*.jpg"))
        image_path = random.choice(candidates)

    top, bottom = make_captions(story)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = re.sub(r"\W+", "_", story["headline"])[:40].strip("_").lower()
    out = OUTPUT_DIR / f"meme_{slug}_{ts}.png"
    render_meme(image_path, top, bottom, out)

    # Recorded so instagram_publisher.py (run as a later CI step, after the
    # image is pushed to `main` and reachable at a public raw URL) knows
    # which file + caption to post without re-deriving them.
    LAST_MEME_FILE.write_text(
        json.dumps({
            "path": str(out.relative_to(BASE)).replace("\\", "/"),
            "caption": story["headline"],
        }, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )

    mark_used(story["headline"])
    print(f"\nDone: {out}")


if __name__ == "__main__":
    main()
