"""Step 1 (06:00) - fetch trending Telugu/Hindi stories from newsdata.io + RSS.

Fetches newsdata.io's /latest endpoint and all configured RSS feeds
concurrently. newsdata.io is queried with country/language/category params
so its results are already relevant (real Telugu-script articles) - those are
kept as-is. RSS entries (often English-titled even on Telugu sites) are
additionally filtered by keyword relevance. Both are ranked by recency +
engagement potential and the top N are written to data/news_cache.json for
emotion_matcher.py to consume.

Run standalone for isolated testing:
    python news_scraper.py
    python news_scraper.py --offline   # no network calls, uses built-in sample data
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
from pathlib import Path
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import aiohttp
import feedparser

from config_loader import get_logger, load_config

# Sample data lets the module (and downstream emotion_matcher/reaction_picker)
# be exercised end-to-end without a NewsAPI key or network access.
SAMPLE_STORIES = [
    {
        "title": "Pawan Kalyan's new film opens to record box office collections",
        "description": "The blockbuster opening sets a new benchmark for Telugu cinema this year.",
        "url": "https://example.com/news/1",
        "source": "SampleWire",
        "published_at": "2026-07-04T04:00:00+00:00",
        "language": "te",
    },
    {
        "title": "Box office collections drop sharply on day 3, trade circles skeptical",
        "description": "Analysts question the film's word-of-mouth after a weak weekday hold.",
        "url": "https://example.com/news/2",
        "source": "SampleWire",
        "published_at": "2026-07-04T02:30:00+00:00",
        "language": "te",
    },
    {
        "title": "Viral video of political rally sparks troll storm on social media",
        "description": "A clip from the rally has gone viral, triggering memes and troll pages.",
        "url": "https://example.com/news/3",
        "source": "SampleWire",
        "published_at": "2026-07-04T05:10:00+00:00",
        "language": "hi",
    },
]


@dataclass
class NewsItem:
    title: str
    description: str
    url: str
    source: str
    published_at: str  # ISO 8601
    language: str = "und"
    matched_keywords: list[str] = field(default_factory=list)
    score: float = 0.0
    source_type: str = "rss"  # "rss" (needs local keyword filtering) or "newsdataio" (pre-filtered server-side)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _parse_datetime(raw: str | None) -> datetime:
    if not raw:
        return datetime.now(timezone.utc)
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        pass
    try:
        # newsdata.io's pubDate format: "2026-07-03 22:59:15" (UTC, per pubDateTZ)
        return datetime.strptime(raw, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError:
        pass
    try:
        return parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        return datetime.now(timezone.utc)


async def fetch_newsdataio(cfg: dict[str, Any], logger) -> list[NewsItem]:
    """Fetch from newsdata.io's /latest endpoint. Returns [] (logged) on any failure.

    country/language/category are passed as query params, so results are
    already relevant real-script Telugu/Hindi articles - no local keyword
    filtering is applied to these (see source_type="newsdataio" handling in
    filter_and_rank).
    """
    news_cfg = cfg["news"]
    api_key = news_cfg["newsdataio_key"]
    if not api_key:
        logger.warning("NEWSDATA_API_KEY not set - skipping newsdata.io fetch (RSS feeds will still run)")
        return []

    params = dict(news_cfg["newsdataio_params"])
    params["apikey"] = api_key
    timeout = aiohttp.ClientTimeout(total=news_cfg["request_timeout_seconds"])

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(news_cfg["newsdataio_endpoint"], params=params) as resp:
                payload = await resp.json()
                if resp.status != 200 or payload.get("status") != "success":
                    logger.error(f"newsdata.io returned HTTP {resp.status}: {str(payload)[:300]}")
                    return []
    except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
        logger.error(f"newsdata.io fetch failed: {exc}")
        return []

    items = []
    for article in payload.get("results", []):
        items.append(
            NewsItem(
                title=article.get("title") or "",
                description=article.get("description") or "",
                url=article.get("link") or "",
                source=article.get("source_name") or article.get("source_id") or "newsdata.io",
                published_at=article.get("pubDate") or datetime.now(timezone.utc).isoformat(),
                language=article.get("language", "und"),
                matched_keywords=article.get("category") or [],
                source_type="newsdataio",
            )
        )
    logger.info(f"newsdata.io: fetched {len(items)} articles")
    return items


def _parse_one_rss_feed(feed_cfg: dict[str, str], logger) -> list[NewsItem]:
    """Synchronous feedparser call - run inside asyncio.to_thread for concurrency."""
    try:
        parsed = feedparser.parse(feed_cfg["url"])
    except Exception as exc:  # feedparser rarely raises, but network layers can
        logger.error(f"RSS fetch failed for {feed_cfg['name']}: {exc}")
        return []

    if parsed.bozo and not parsed.entries:
        logger.error(f"RSS feed unparseable for {feed_cfg['name']}: {parsed.bozo_exception}")
        return []

    items = []
    for entry in parsed.entries:
        published = entry.get("published") or entry.get("updated")
        items.append(
            NewsItem(
                title=entry.get("title", ""),
                description=entry.get("summary", ""),
                url=entry.get("link", ""),
                source=feed_cfg["name"],
                published_at=_parse_datetime(published).isoformat(),
                language=feed_cfg.get("language", "und"),
            )
        )
    logger.info(f"RSS[{feed_cfg['name']}]: fetched {len(items)} entries")
    return items


async def fetch_all_rss(cfg: dict[str, Any], logger) -> list[NewsItem]:
    feeds = cfg["news"]["rss_feeds"]
    tasks = [asyncio.to_thread(_parse_one_rss_feed, feed, logger) for feed in feeds]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    items: list[NewsItem] = []
    for feed, result in zip(feeds, results):
        if isinstance(result, Exception):
            logger.error(f"RSS task crashed for {feed['name']}: {result}")
            continue
        items.extend(result)
    return items


def filter_and_rank(items: list[NewsItem], cfg: dict[str, Any], logger) -> list[NewsItem]:
    keywords = [k.lower() for k in cfg["news"]["keywords"]]
    half_life = cfg["news"]["recency_half_life_hours"]
    now = datetime.now(timezone.utc)

    relevant = []
    for item in items:
        if item.source_type in ("newsdataio", "telegram"):
            # These sources are pre-filtered at origin (newsdata.io by API params,
            # Telegram by channel selection). Telugu-script text won't match the
            # English keyword list, so skip local keyword filtering for both.
            matched = item.matched_keywords or [item.source_type]
        else:
            haystack = f"{item.title} {item.description}".lower()
            matched = [kw for kw in keywords if kw in haystack]
            if not matched:
                continue
            item.matched_keywords = matched

        published = _parse_datetime(item.published_at)
        if published.tzinfo is None:
            published = published.replace(tzinfo=timezone.utc)
        age_hours = max((now - published).total_seconds() / 3600, 0)
        recency_score = math.exp(-math.log(2) * age_hours / half_life)
        engagement_score = 1 + 0.3 * len(matched)
        item.score = round(recency_score * engagement_score, 4)
        relevant.append(item)

    relevant.sort(key=lambda i: i.score, reverse=True)

    # newsdata.io items are delayed ~12h by the free tier and would be
    # outscored on recency alone, but they carry real Telugu-script text.
    # Telegram items are very fresh but unscored (score=0 until filter_and_rank
    # runs). Reserve floor slots for both so neither gets crowded out by RSS.
    max_stories = cfg["news"]["max_stories"]
    min_newsdataio = cfg["news"]["min_newsdataio_stories"]
    min_telegram = cfg["news"].get("min_telegram_stories", 3)

    reserved_ndi = [i for i in relevant if i.source_type == "newsdataio"][:min_newsdataio]
    reserved_tg  = [i for i in relevant if i.source_type == "telegram"][:min_telegram]
    reserved = reserved_ndi + reserved_tg
    reserved_ids = {id(i) for i in reserved}
    remaining_slots = max_stories - len(reserved)
    fill = [i for i in relevant if id(i) not in reserved_ids][:remaining_slots]
    top = sorted(reserved + fill, key=lambda i: i.score, reverse=True)

    logger.info(
        f"Filtered {len(items)} raw items -> {len(relevant)} relevant -> top {len(top)} kept "
        f"({len(reserved_ndi)} newsdata.io + {len(reserved_tg)} telegram reserved)"
    )
    return top


def load_telegram_cache(cfg: dict[str, Any], logger) -> list[NewsItem]:
    """Load items written by telegram_scraper.py (runs on Termux, pushes to repo).
    Returns [] silently if the file doesn't exist yet."""
    cache_path = Path(cfg["paths"].get("telegram_cache_file", "data/telegram_cache.json"))
    if not cache_path.exists():
        return []
    try:
        with open(cache_path, encoding="utf-8") as f:
            raw = json.load(f)
        items = [NewsItem(**r) for r in raw]
        logger.info(f"Telegram cache: loaded {len(items)} items from {cache_path}")
        return items
    except Exception as exc:
        logger.warning(f"Could not load telegram cache ({exc}) - skipping")
        return []


async def fetch_trending_stories(cfg: dict[str, Any], logger, offline: bool = False) -> list[NewsItem]:
    if offline:
        logger.info("Offline mode: using built-in sample stories instead of live APIs")
        items = [NewsItem(**s) for s in SAMPLE_STORIES]
        return filter_and_rank(items, cfg, logger)

    newsdataio_task = fetch_newsdataio(cfg, logger)
    rss_task = fetch_all_rss(cfg, logger)
    newsdataio_items, rss_items = await asyncio.gather(newsdataio_task, rss_task)
    telegram_items = load_telegram_cache(cfg, logger)

    all_items = newsdataio_items + rss_items + telegram_items
    if not all_items:
        logger.warning("No news items fetched from any source this run")
    return filter_and_rank(all_items, cfg, logger)


def save_cache(items: list[NewsItem], cfg: dict[str, Any]) -> None:
    cache_path = cfg["paths"]["news_cache_file"]
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump([i.to_dict() for i in items], f, ensure_ascii=False, indent=2)


async def run_pipeline_step(cfg: dict[str, Any], logger, offline: bool = False) -> list[NewsItem]:
    """Fetch, rank, and cache stories. Called by both the CLI and scheduler.py."""
    items = await fetch_trending_stories(cfg, logger, offline=offline)
    save_cache(items, cfg)
    logger.info(f"Saved {len(items)} ranked stories to {cfg['paths']['news_cache_file']}")
    for item in items:
        logger.info(f"  [{item.score:.3f}] ({item.source}) {item.title}")
    return items


async def main() -> list[NewsItem]:
    parser = argparse.ArgumentParser(description="Fetch trending Telugu/Hindi news stories")
    parser.add_argument("--offline", action="store_true", help="Use sample data, no network calls")
    args = parser.parse_args()

    cfg = load_config()
    logger = get_logger("news_scraper", cfg)
    return await run_pipeline_step(cfg, logger, offline=args.offline)


if __name__ == "__main__":
    asyncio.run(main())
