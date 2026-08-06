"""Trend signal aggregator for ideation.

Pulls a small, fresh sample of what's trending across three free public feeds:
  - Google Trends daily RSS (IN + US)  -- broad "what's hot today"
  - HackerNews Firebase API top stories -- AI/tech signal
  - Reddit hot on r/Entrepreneur, r/sidehustle, r/passive_income -- hustle signal

Writes a combined snapshot to data/trend_cache.json with a 6-hour TTL. On
cache hit within TTL, does no network calls. On per-source failure, drops
that source silently -- callers get whatever partial signal is available.

Public entry point:
  get_pillar_candidates(pillar_id: str, limit: int = 8) -> list[dict]

Each candidate: {title, source, url, snippet?, score?}

Pillar -> source routing (see _PILLAR_SOURCES). Evergreen pillars get a
loose Google Trends pull; ai_tools + wealth pillars get their own
targeted feeds mixed in.

Standalone run:
  python -m engine.trends.fetch          # refresh + print per-pillar sample
  python -m engine.trends.fetch --pillar ai_tools_workflows
  python -m engine.trends.fetch --force  # ignore cache
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

import requests


_BASE = Path(__file__).parent.parent.parent
_CACHE_PATH = _BASE / "data" / "trend_cache.json"
_FIRST_SEEN_PATH = _BASE / "data" / "trend_first_seen.json"
_CACHE_TTL_SEC = 6 * 3600
_HTTP_TIMEOUT = 12
_UA = "MemeFactory/1.0 (+https://github.com/vaibhav018/MemeFactory)"


# ── source fetchers ────────────────────────────────────────────────────────

def _google_trends_rss(geo: str) -> list[dict]:
    """Daily trending searches RSS. `geo` is 'IN' or 'US'.

    Endpoint is /trending/rss (Google renamed from the old
    /trends/trendingsearches/daily/rss in 2024).
    """
    url = f"https://trends.google.com/trending/rss?geo={geo}"
    r = requests.get(url, headers={"User-Agent": _UA}, timeout=_HTTP_TIMEOUT)
    r.raise_for_status()
    root = ET.fromstring(r.content)
    items = []
    ns = {"ht": "https://trends.google.com/trending/rss"}
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        if not title:
            continue
        approx = item.findtext("ht:approx_traffic", default="", namespaces=ns)
        news_title = item.findtext("ht:news_item/ht:news_item_title",
                                   default="", namespaces=ns)
        news_url = item.findtext("ht:news_item/ht:news_item_url",
                                 default="", namespaces=ns)
        items.append({
            "title": title,
            "source": f"google_trends_{geo.lower()}",
            "url": news_url or url,
            "snippet": news_title,
            "score": _traffic_to_score(approx),
        })
    return items


def _traffic_to_score(approx: str) -> float:
    """'2M+' -> 2_000_000 style rough score for ranking."""
    if not approx:
        return 0.0
    s = approx.replace("+", "").replace(",", "").strip().upper()
    mult = 1
    if s.endswith("M"):
        mult, s = 1_000_000, s[:-1]
    elif s.endswith("K"):
        mult, s = 1_000, s[:-1]
    try:
        return float(s) * mult
    except ValueError:
        return 0.0


def _hackernews(top_n: int = 30) -> list[dict]:
    ids = requests.get(
        "https://hacker-news.firebaseio.com/v0/topstories.json",
        timeout=_HTTP_TIMEOUT,
    ).json()[:top_n]
    items = []
    for hid in ids:
        try:
            it = requests.get(
                f"https://hacker-news.firebaseio.com/v0/item/{hid}.json",
                timeout=_HTTP_TIMEOUT,
            ).json()
        except Exception:
            continue
        if not it or it.get("type") != "story":
            continue
        title = (it.get("title") or "").strip()
        if not title:
            continue
        items.append({
            "title": title,
            "source": "hackernews",
            "url": it.get("url") or f"https://news.ycombinator.com/item?id={hid}",
            "snippet": "",
            "score": float(it.get("score", 0)),
        })
    return items


def _reddit_hot(subreddit: str, top_n: int = 15) -> list[dict]:
    """Reddit's .json endpoints are aggressively blocked for generic UAs; the
    per-subreddit Atom feed still works and gives us title + link + summary,
    which is all ideation needs. No score is exposed by RSS, so we default it
    to 0 (round-robin interleaving in the aggregator handles ranking anyway).
    """
    url = f"https://www.reddit.com/r/{subreddit}/hot/.rss?limit={top_n}"
    r = requests.get(url, headers={"User-Agent": _UA}, timeout=_HTTP_TIMEOUT)
    r.raise_for_status()
    root = ET.fromstring(r.content)
    atom = "{http://www.w3.org/2005/Atom}"
    items = []
    for entry in root.iter(f"{atom}entry"):
        title = (entry.findtext(f"{atom}title") or "").strip()
        if not title:
            continue
        link_el = entry.find(f"{atom}link")
        href = link_el.get("href") if link_el is not None else ""
        summary = (entry.findtext(f"{atom}content") or "").strip()
        items.append({
            "title": title,
            "source": f"reddit_{subreddit.lower()}",
            "url": href,
            "snippet": summary[:200],
            "score": 0.0,
        })
    return items


# ── aggregation + cache ────────────────────────────────────────────────────

_SOURCES = {
    "google_trends_in":     lambda: _google_trends_rss("IN"),
    "google_trends_us":     lambda: _google_trends_rss("US"),
    "hackernews":           lambda: _hackernews(30),
    # Reddit throttles hard after ~1 rapid unauth request per IP -- one
    # subreddit is plenty. r/Entrepreneur returns 15 posts, which covers
    # the hustle/wealth pillar's needs.
    "reddit_entrepreneur":  lambda: _reddit_hot("Entrepreneur"),
}

# Which sources feed which pillars. Order = preference; aggregator interleaves.
# Profit Prompts runs only two pillars (AI + Wealth); evergreen pillars were
# retired 2026-08-01 to keep the account tight-focus on brand tagline
# "AI Tools • Earning Strategies".
_PILLAR_SOURCES: dict[str, list[str]] = {
    "ai_tools_workflows": ["hackernews", "google_trends_us", "google_trends_in"],
    "wealth_hustles":     ["reddit_entrepreneur", "google_trends_in",
                           "google_trends_us"],
    "tech_science":       ["hackernews", "google_trends_us"],
}


def _refresh() -> dict:
    """Fetch every source, ignoring per-source failures.

    Reddit's public feeds throttle aggressively after ~1 rapid request, so we
    space out Reddit calls with a short sleep. Other sources fire immediately.
    """
    snapshot = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "sources": {},
        "errors": {},
    }
    for name, fetcher in _SOURCES.items():
        try:
            snapshot["sources"][name] = fetcher()
        except Exception as e:
            snapshot["errors"][name] = f"{type(e).__name__}: {e}"
    _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CACHE_PATH.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False))
    return snapshot


_SOURCE_PREFIX_RE = re.compile(r"^\s*\[[^\]]+\]\s*")


def _normalize_title(title: str) -> str:
    """Case-fold + collapse whitespace so equivalent titles resolve to one key.

    Also strips a leading '[source_name] ' prefix — Claude tends to copy the
    prompt's display format ('[hackernews] Some Title') into trend_source
    verbatim, so lookups need to survive that.
    """
    stripped = _SOURCE_PREFIX_RE.sub("", title)
    return " ".join(stripped.strip().lower().split())


def _load_first_seen() -> dict:
    if not _FIRST_SEEN_PATH.exists():
        return {}
    try:
        return json.loads(_FIRST_SEEN_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _update_first_seen(snapshot: dict) -> None:
    """Record first-seen timestamp for every trend title we haven't seen before.

    Freshness is defined by when a title FIRST appeared in our cache, not by
    the cache-refresh timestamp — a Google Trends daily list can re-list the
    same title for 2-3 days but the topic itself is stale after 48h.
    """
    log = _load_first_seen()
    now = datetime.now(timezone.utc).isoformat()
    changed = False
    for items in snapshot.get("sources", {}).values():
        for it in items:
            key = _normalize_title(it.get("title", ""))
            if key and key not in log:
                log[key] = now
                changed = True
    if changed:
        _FIRST_SEEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        _FIRST_SEEN_PATH.write_text(json.dumps(log, indent=2, ensure_ascii=False))


def get_trend_age_hours(title: str) -> float | None:
    """Return hours since this trend title was first seen in our cache.

    Returns None if the title has never been logged (either it never existed
    in a snapshot, or Claude hallucinated it). Callers should treat None as
    'unverifiable' — usually a reject signal for the freshness gate.
    """
    key = _normalize_title(title)
    if not key:
        return None
    log = _load_first_seen()
    ts = log.get(key)
    if not ts:
        return None
    try:
        first = datetime.fromisoformat(ts)
    except ValueError:
        return None
    return (datetime.now(timezone.utc) - first).total_seconds() / 3600.0


def _load_or_refresh(force: bool = False) -> dict:
    snap = None
    if not force and _CACHE_PATH.exists():
        try:
            snap = json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
            fetched_at = datetime.fromisoformat(snap["fetched_at"])
            age = (datetime.now(timezone.utc) - fetched_at).total_seconds()
            if age >= _CACHE_TTL_SEC:
                snap = None
        except Exception:
            snap = None
    if snap is None:
        snap = _refresh()
    # Populate first-seen log on every load, not just on refresh — otherwise
    # the log stays empty for the entire cache-hit window and gate 8 falsely
    # rejects everything as unverifiable.
    _update_first_seen(snap)
    return snap


def get_pillar_candidates(pillar_id: str, limit: int = 8,
                          force_refresh: bool = False) -> list[dict]:
    """Return top-N trend candidates for a pillar, ranked by source score.

    Interleaves the pillar's preferred sources round-robin so the top of the
    list reflects source diversity rather than one hot subreddit crowding out
    the rest. Falls back to google_trends_us if pillar has no mapping.
    """
    try:
        snap = _load_or_refresh(force=force_refresh)
    except Exception:
        return []

    src_names = _PILLAR_SOURCES.get(pillar_id)
    if not src_names:
        return []
    per_source: dict[str, list[dict]] = {}
    for name in src_names:
        raw = snap["sources"].get(name, [])
        per_source[name] = sorted(raw, key=lambda x: x.get("score", 0), reverse=True)

    # round-robin interleave until limit reached or all buckets empty
    picked: list[dict] = []
    seen_titles: set[str] = set()
    idx = 0
    while len(picked) < limit:
        made_progress = False
        for name in src_names:
            bucket = per_source.get(name, [])
            if idx < len(bucket):
                cand = bucket[idx]
                key = cand["title"].lower()
                if key not in seen_titles:
                    picked.append(cand)
                    seen_titles.add(key)
                    made_progress = True
                    if len(picked) >= limit:
                        break
        if not made_progress:
            break
        idx += 1
    return picked


# ── CLI ────────────────────────────────────────────────────────────────────

def _main() -> None:
    parser = argparse.ArgumentParser(description="MemeFactory trend fetcher")
    parser.add_argument("--pillar", help="Print candidates for one pillar id")
    parser.add_argument("--force", action="store_true", help="Ignore cache")
    parser.add_argument("--limit", type=int, default=8)
    args = parser.parse_args()

    snap = _load_or_refresh(force=args.force)
    print(f"fetched_at: {snap['fetched_at']}")
    for name, items in snap["sources"].items():
        print(f"  {name}: {len(items)} items")
    if snap.get("errors"):
        print("errors:")
        for name, err in snap["errors"].items():
            print(f"  {name}: {err}")

    pillar_ids = [args.pillar] if args.pillar else list(_PILLAR_SOURCES.keys())
    for pid in pillar_ids:
        print(f"\n--- {pid} (top {args.limit}) ---")
        for i, c in enumerate(get_pillar_candidates(pid, limit=args.limit), 1):
            print(f"  {i}. [{c['source']}] {c['title']}")


if __name__ == "__main__":
    _main()
