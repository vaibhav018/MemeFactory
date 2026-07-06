#!/usr/bin/env python3
"""
AUTO MEME - the scheduled pipeline for @bhogeswar_rao_garu
==========================================================
One run = one meme:
  1. Fetch trending headlines from direct outlet RSS feeds (Sakshi,
     123telugu, TV9 Telugu, Times of India, Sportstar Cricket)
  2. Pick the freshest unused headline (Tollywood first)
  3. Download a related, strictly-filtered news photo (DuckDuckGo image
     search: safesearch on, trusted-domain-only, no unrelated fallback)
  4. Render it in the page's news-card format (meme_factory.py), with
     face-aware cropping so photos of people don't get their heads cut off,
     plus the Bhogeswar Rao garu watermark
  5. Fetch the real article text and summarize it locally (content_summarizer.py,
     a free open-source model - no paid API) for the Instagram post caption;
     falls back to the bare headline if that fails for any reason
  6. Remember the headline so it's never reused

Runs at 8AM / 1PM / 9PM via Windows Task Scheduler (see run_meme_bot.bat).
Run manually anytime:  python auto_meme.py

NOTE: the image's own top caption is just the headline (user's call: no
canned punchlines/clutter). A bottom bar renders only when a meme explicitly
supplies real content lines (see meme_factory.MEME for manual use).

This supersedes the older scheduler.py/news_scraper.py pipeline (built for
the old reaction-image format; never activated - its deps aren't installed).
"""

import json
import random
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime

# Sakshi headlines are pure Telugu script - on a non-UTF-8 console (default
# on Windows, cp1252) plain print() would crash with UnicodeEncodeError.
# GitHub Actions runners already default to UTF-8, so this only matters for
# local/manual runs, but it's a one-line safety net either way.
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from pathlib import Path

import requests

# reuse the renderer + image fetcher from meme_factory
from meme_factory import (DOWNLOAD_DIR, OUTPUT_DIR, REACTION_DIR, WHITE,
                          YELLOW, fetch_news_image, render_meme)
from content_summarizer import write_content_caption

BASE = Path(__file__).resolve().parent      # portable: repo root, any OS
DATA_DIR = BASE / "data"
DATA_DIR.mkdir(exist_ok=True)
USED_FILE = DATA_DIR / "used_headlines.json"
LAST_MEME_FILE = DATA_DIR / "last_meme.json"

# ---------------------------------------------------------------- news feed
# category -> direct outlet RSS feed (NOT Google News search RSS - Google's
# links are client-side JS redirects to an interstitial page, not real HTTP
# redirects, so there is no article body reachable through them at all).
# Direct outlet feeds give real article URLs that content_summarizer.py can
# actually fetch and summarize. Verified live before wiring in - see commit.
FEEDS = [
    ("tollywood", "https://www.123telugu.com/feed"),
    ("andhra_telangana", "https://www.sakshi.com/rss.xml"),
    ("andhra_telangana", "https://tv9telugu.com/feed"),
    ("cricket", "https://sportstar.thehindu.com/cricket/feeder/default.rss"),
    ("national", "https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms"),
]
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def clean_title(title: str) -> str:
    """Strip the ' - Source Name' suffix and truncated trailing fragments."""
    title = re.sub(r"\s+-\s+[^-]+$", "", title).strip()
    if ";" in title:
        title = title.split(";")[0].strip()
    return title


def fetch_headlines() -> list[dict]:
    items = []
    for category, url in FEEDS:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            root = ET.fromstring(resp.content)
        except Exception as e:
            print(f"!! {category} ({url}): feed failed ({e})")
            continue
        count = 0
        for item in root.iter("item"):
            title = clean_title(item.findtext("title", ""))
            if not title or len(title) < 25 or len(title) > 160:
                continue
            items.append({"category": category, "headline": title, "link": item.findtext("link", "")})
            count += 1
            if count >= 8:
                break
        print(f">> {category}: {count} headlines from {url}")
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


def _strip_punctuation(text: str) -> str:
    """Like re.sub(r"[^\\w\\s']", " ", text), but Unicode-aware for scripts
    like Telugu: Python's \\w excludes combining marks (category M), and
    Telugu vowel signs / the virama are combining marks - the plain regex
    was shattering Telugu words into single detached consonants."""
    import unicodedata
    return "".join(
        ch if (ch.isalnum() or ch.isspace() or ch == "'" or unicodedata.category(ch).startswith("M"))
        else " "
        for ch in text
    )

CATEGORY_SUFFIX = {
    "tollywood": "Telugu movie",
    "andhra_telangana": "Telangana Andhra news",
    "cricket": "India cricket match",
    "national": "India",
}

# ---------------------------------------------------------------- hashtags
CATEGORY_HASHTAGS = {
    "tollywood": ["#Tollywood", "#TeluguCinema", "#TeluguMovies", "#TFI"],
    "andhra_telangana": ["#Telangana", "#AndhraPradesh", "#TeluguNews"],
    "cricket": ["#Cricket", "#TeamIndia", "#INDCricket"],
    "national": ["#India", "#Trending", "#ViralNews"],
}
COMMON_HASHTAGS = ["#TeluguMemes", "#TeluguTrolls", "#TeluguComedy", "#Meme", "#Viral", "#Reels"]
MAX_HASHTAGS = 12


def build_hashtags(story: dict, keyword: str | None) -> list[str]:
    """Category tags + one dynamic tag from the story's subject + common reach tags."""
    tags = list(CATEGORY_HASHTAGS.get(story["category"], []))
    if keyword:
        kw_tag = "#" + re.sub(r"[^A-Za-z0-9]", "", keyword)
        if len(kw_tag) > 1:
            tags.append(kw_tag)
    tags += COMMON_HASHTAGS

    seen, deduped = set(), []
    for tag in tags:
        if tag.lower() not in seen:
            seen.add(tag.lower())
            deduped.append(tag)
    return deduped[:MAX_HASHTAGS]


def extract_image_query(story: dict) -> tuple[str, str | None]:
    """Distill the headline into a focused image query + a relevance keyword.

    'Nagabandham Box Office Collection Day 1: Registers ...' ->
    ('Nagabandham Telugu movie', 'Nagabandham')
    """
    subject = re.split(r"[:\-–|]", story["headline"])[0]
    subject = FILLER.sub(" ", subject)
    subject = _strip_punctuation(subject)
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
    slug = "_".join(_strip_punctuation(story["headline"]).split())[:40].strip("_").lower()
    out = OUTPUT_DIR / f"meme_{slug}_{ts}.jpg"
    render_meme(image_path, top, bottom, out)

    # Recorded so instagram_publisher.py (run as a later CI step, after the
    # image is pushed to `main` and reachable at a public raw URL) knows
    # which file + caption to post without re-deriving them.
    hashtags = build_hashtags(story, keyword)
    # The image already shows the headline as its own top caption - repeating
    # it here added nothing, so the post caption is a real summary of the
    # actual article instead (falls back to the bare headline if the article
    # can't be fetched/summarized for any reason - free local model, no API).
    content_caption = write_content_caption(story.get("link", "")) or story["headline"]
    caption = content_caption + "\n.\n.\n" + " ".join(hashtags)
    LAST_MEME_FILE.write_text(
        json.dumps({
            "path": str(out.relative_to(BASE)).replace("\\", "/"),
            "caption": caption,
        }, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )

    mark_used(story["headline"])
    print(f"\nDone: {out}")


if __name__ == "__main__":
    main()
