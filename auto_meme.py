#!/usr/bin/env python3
"""
AUTO MEME - the scheduled pipeline for @bhogeswar_rao_garu
==========================================================
One run = one meme:
  1. Fetch trending headlines from direct outlet RSS feeds (Sakshi,
     123telugu, TV9 Telugu, Times of India, Sportstar Cricket, BBC World)
  2. Pick the freshest unused headline (Tollywood first, but capped at 50%
     of posts over the last 20 - see movie_news_over_cap - so movie news
     doesn't crowd out local/national/international/cricket) that also has
     a genuinely matching online photo - see step 3. Headlines whose search
     turns up nothing suitable are marked used and skipped in favor of the
     next one; if none in the batch have a real photo, no meme is generated
     for this run at all (quality over always posting something).
  3. Download a related, strictly-filtered news photo (DuckDuckGo image
     search: safesearch on, trusted-domain-only). No local reaction-image
     fallback anymore - a mismatched reaction photo on a sensitive story
     (e.g. a comedic reaction image under a hospital-visit headline) is
     worse than not posting.
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
from urllib.parse import urlparse

import requests

# reuse the renderer + image fetcher from meme_factory
from meme_factory import (DOWNLOAD_DIR, OUTPUT_DIR, WHITE,
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
    ("tollywood",        "https://www.123telugu.com/feed"),
    ("andhra_telangana", "https://tv9telugu.com/feed"),
    ("andhra_telangana", "https://www.thehansindia.com/feeds/telugu-news.xml"),
    ("cricket",          "https://sportstar.thehindu.com/cricket/feeder/default.rss"),
    ("national",         "https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms"),
    ("international",    "http://feeds.bbci.co.uk/news/world/rss.xml"),
]

# Movie news was crowding out everything else (123telugu has the deepest,
# freshest supply of candidates each run, and was always tried first). Capped
# at 50% over a rolling window of recent posts - once tollywood hits that
# share, it's excluded from candidates for the run until older posts age out
# of the window and bring the ratio back down.
MOVIE_CATEGORY = "tollywood"
MOVIE_NEWS_CAP = 0.5
CATEGORY_HISTORY_WINDOW = 20
CATEGORY_HISTORY_FILE = DATA_DIR / "category_history.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def clean_title(title: str) -> str:
    """Strip the ' - Source Name' suffix and truncated trailing fragments."""
    title = re.sub(r"\s+-\s+[^-]+$", "", title).strip()
    if ";" in title:
        title = title.split(";")[0].strip()
    return title


# 123telugu (and similar entertainment outlets) route photo-gallery/slideshow
# listings through a separate "gallery." subdomain and titles like "Latest
# Photos : Name" / "Glamorous Pics : Name" - these aren't news stories at all
# (no real headline content to summarize, and they routinely fail image
# search, silently falling back to an unrelated reaction image). Filter them
# out at the source rather than relying on the length check to catch them.
_GALLERY_TITLE_RE = re.compile(
    r"^(new|latest|glamorous)?\s*(photos?|pics?|stills?)\s*:", re.I
)


def _is_gallery_item(title: str, link: str) -> bool:
    if _GALLERY_TITLE_RE.match(title):
        return True
    try:
        netloc = urlparse(link).netloc.lower()
    except Exception:
        return False
    return netloc.startswith("gallery.") or "/slideshows/" in link.lower()


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
            link = item.findtext("link", "")
            if not title or len(title) < 25 or len(title) > 160:
                continue
            if _is_gallery_item(title, link):
                continue
            items.append({"category": category, "headline": title, "link": link})
            count += 1
            if count >= 8:
                break
        print(f">> {category}: {count} headlines from {url}")
    return items


TELEGRAM_CACHE_FILE = DATA_DIR / "telegram_cache.json"


def load_telegram_headlines() -> list[dict]:
    """Load headlines from telegram_scraper.py's cache (written on Termux, committed to repo).
    Messages are already the headline text — use the first line as the headline."""
    if not TELEGRAM_CACHE_FILE.exists():
        return []
    try:
        items = json.loads(TELEGRAM_CACHE_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"!! telegram cache unreadable: {e}")
        return []
    out = []
    for item in items:
        title = (item.get("title") or "").strip()
        if not title or len(title) < 25 or len(title) > 200:
            continue
        out.append({
            "category": "andhra_telangana",
            "headline": title,
            "link": item.get("url", ""),
        })
    if out:
        print(f">> telegram_cache: {len(out)} headlines loaded")
    return out


def load_used() -> list:
    if USED_FILE.exists():
        return json.loads(USED_FILE.read_text(encoding="utf-8"))
    return []


def mark_used(headline: str):
    used = load_used()
    used.append(headline)
    USED_FILE.write_text(json.dumps(used[-500:], ensure_ascii=False, indent=1),
                         encoding="utf-8")


def load_category_history() -> list:
    if CATEGORY_HISTORY_FILE.exists():
        return json.loads(CATEGORY_HISTORY_FILE.read_text(encoding="utf-8"))
    return []


def record_category(category: str):
    history = load_category_history()
    history.append(category)
    CATEGORY_HISTORY_FILE.write_text(
        json.dumps(history[-CATEGORY_HISTORY_WINDOW:], ensure_ascii=False, indent=1),
        encoding="utf-8",
    )


def movie_news_over_cap() -> bool:
    history = load_category_history()
    if not history:
        return False
    return history.count(MOVIE_CATEGORY) / len(history) >= MOVIE_NEWS_CAP


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
    "international": "world news",
}

# ---------------------------------------------------------------- hashtags
CATEGORY_HASHTAGS = {
    "tollywood": ["#Tollywood", "#TeluguCinema", "#TeluguMovies", "#TFI"],
    "andhra_telangana": ["#Telangana", "#AndhraPradesh", "#TeluguNews"],
    "cricket": ["#Cricket", "#TeamIndia", "#INDCricket"],
    "national": ["#India", "#Trending", "#ViralNews"],
    "international": ["#World", "#International", "#GlobalNews", "#Trending"],
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
def _split_headline(headline: str) -> list[tuple[str, tuple]]:
    """Split a headline into (text, color) chunks for two-tone rendering.

    Handles three break patterns in priority order:
      1. "Subject: detail" or "Subject, detail" (English + Telugu with colon)
      2. "Hook..! detail" — common Telugu news format (V6, TV9, Sakshi)
      3. "Hook.. detail"  — Telugu ellipsis used as a soft break
      4. Fallback: first ~1/3 of words in yellow, rest white
    """
    # Pattern 1: colon/comma split — cap hook at 55% so one word isn't all yellow
    m = re.match(r"^(.+?[,:])\s*(.+)$", headline)
    if m and len(m.group(1)) < len(headline) * 0.55:
        return [(m.group(1).rstrip(",:").strip(), YELLOW), (m.group(2).strip(), WHITE)]

    # Pattern 2: "hook..! rest" or "hook..? rest"
    m = re.match(r"^(.+?\.\.+[!?])\s*(.+)$", headline)
    if m:
        return [(m.group(1).strip(), YELLOW), (m.group(2).strip(), WHITE)]

    # Pattern 3: "hook..  rest" (Telugu ellipsis as break, space after)
    m = re.match(r"^(.+?)\.\.\s+(.+)$", headline)
    if m:
        return [(m.group(1).strip(), YELLOW), (m.group(2).strip(), WHITE)]

    # Fallback: first ~1/3 of words yellow, rest white
    words = headline.split()
    split = max(1, len(words) // 3)
    return [(" ".join(words[:split]), YELLOW), (" ".join(words[split:]), WHITE)]


def make_captions(story: dict, content_caption: str | None):
    top = _split_headline(story["headline"])

    bottom = []
    if content_caption:
        sentences = [s.strip() for s in content_caption.split(".") if s.strip()]
        for i, sentence in enumerate(sentences[:3]):
            bottom.append((sentence, YELLOW if i == 0 else WHITE))

    return top, bottom


# ---------------------------------------------------------------- main
def main():
    print("=" * 70)
    print(f"AUTO MEME run @ {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 70)

    items = fetch_headlines() + load_telegram_headlines()
    if not items:
        sys.exit("!! No headlines fetched - aborting this run.")

    if movie_news_over_cap():
        print(f"!! Movie news is at/above the {int(MOVIE_NEWS_CAP*100)}% cap over the last "
              f"{CATEGORY_HISTORY_WINDOW} posts - excluding {MOVIE_CATEGORY} candidates this run")
        items = [i for i in items if i["category"] != MOVIE_CATEGORY]

    # Try candidates in feed-priority order until one has a genuinely
    # matching online photo. A headline whose search turns up nothing
    # suitable is marked used (so it isn't retried forever) and skipped in
    # favor of the next one - no local reaction-image fallback, since a
    # mismatched reaction photo on a sensitive story is worse than skipping.
    used = set(load_used())
    story = image_path = query = keyword = None
    for candidate in items:
        if candidate["headline"] in used:
            continue
        q, kw = extract_image_query(candidate)
        img = fetch_news_image(q, DOWNLOAD_DIR, must_contain=kw)
        if img is not None:
            story, image_path, query, keyword = candidate, img, q, kw
            break
        print(f"!! No suitable online photo for '{candidate['headline'][:60]}' - trying the next headline")
        mark_used(candidate["headline"])

    if story is None:
        print("!! No headline in this batch had a genuinely matching photo - skipping this run, no meme generated.")
        if LAST_MEME_FILE.exists():
            LAST_MEME_FILE.unlink()
        sys.exit(0)

    print(f">> Picked [{story['category']}]: {story['headline']}")

    # Computed once, up front, and reused for both the on-image bottom bar
    # and the Instagram post caption below. distilbart's decoder sometimes
    # emits a stray space before punctuation ("crore . Trade") - clean that
    # up regardless of where the text ends up.
    raw_summary = write_content_caption(story.get("link", ""))
    content_caption = re.sub(r"\s+([.,])", r"\1", raw_summary) if raw_summary else None

    top, bottom = make_captions(story, content_caption)
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
    caption = (content_caption or story["headline"]) + "\n.\n.\n" + " ".join(hashtags)
    LAST_MEME_FILE.write_text(
        json.dumps({
            "path": str(out.relative_to(BASE)).replace("\\", "/"),
            "caption": caption,
        }, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )

    mark_used(story["headline"])
    record_category(story["category"])
    print(f"\nDone: {out}")


if __name__ == "__main__":
    main()
