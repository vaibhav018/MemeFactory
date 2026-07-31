"""Step 2 (06:15) - assign a meme emotion + punchline to each news story.

Reads data/news_cache.json (written by news_scraper.py), applies the
keyword-based rule-set from config.json's `emotion_rules`, and writes
data/emotion_matched.json for reaction_picker.py to consume.

Run standalone for isolated testing:
    python emotion_matcher.py
"""
from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass
from typing import Any

from config_loader import get_logger, load_config

TOP_CAPTION_MAX_CHARS = 90


@dataclass
class MemeCandidate:
    title: str
    description: str
    url: str
    source: str
    published_at: str
    language: str
    emotion: str
    punchline: str
    top_caption: str
    matched_keywords: list[str]
    score: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_top_caption(title: str, max_chars: int = TOP_CAPTION_MAX_CHARS) -> str:
    """News headlines run long; trim to something that reads well on a meme."""
    title = title.strip()
    if len(title) <= max_chars:
        return title
    truncated = title[:max_chars].rsplit(" ", 1)[0]
    return truncated + "..."


def match_emotion(story: dict[str, Any], rules_cfg: dict[str, Any]) -> tuple[str, list[str], list[str]]:
    """Return (emotion, matched_keywords, punchline_templates) for a story.

    Picks the rule with the most keyword hits; ties broken by rule order.
    Falls back to `default_emotion` when nothing matches.
    """
    haystack = f"{story.get('title', '')} {story.get('description', '')}".lower()

    best_rule = None
    best_hits: list[str] = []
    for rule in rules_cfg["rules"]:
        hits = [kw for kw in rule["keywords"] if kw.lower() in haystack]
        if len(hits) > len(best_hits):
            best_rule = rule
            best_hits = hits

    if best_rule is None or not best_hits:
        default_emotion = rules_cfg["default_emotion"]
        fallback_rule = next(
            (r for r in rules_cfg["rules"] if r["emotion"] == default_emotion),
            rules_cfg["rules"][-1],
        )
        return fallback_rule["emotion"], [], fallback_rule["punchline_templates"]

    return best_rule["emotion"], best_hits, best_rule["punchline_templates"]


def pick_punchline(templates: list[str], rng: random.Random) -> str:
    return rng.choice(templates)


def match_all(stories: list[dict[str, Any]], cfg: dict[str, Any], seed: int | None = None) -> list[MemeCandidate]:
    """Match emotion + punchline for every story. `seed` makes selection
    reproducible for tests; leave None for real randomness in production."""
    rng = random.Random(seed)
    rules_cfg = cfg["emotion_rules"]

    candidates = []
    for story in stories:
        emotion, hits, templates = match_emotion(story, rules_cfg)
        punchline = pick_punchline(templates, rng)
        candidates.append(
            MemeCandidate(
                title=story.get("title", ""),
                description=story.get("description", ""),
                url=story.get("url", ""),
                source=story.get("source", ""),
                published_at=story.get("published_at", ""),
                language=story.get("language", "und"),
                emotion=emotion,
                punchline=punchline,
                top_caption=build_top_caption(story.get("title", "")),
                matched_keywords=hits,
                score=story.get("score", 0.0),
            )
        )
    return candidates


def load_news_cache(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    cache_path = cfg["paths"]["news_cache_file"]
    try:
        with open(cache_path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []


def save_matched(candidates: list[MemeCandidate], cfg: dict[str, Any]) -> str:
    out_path = cfg["_root"] / "data" / "emotion_matched.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump([c.to_dict() for c in candidates], f, ensure_ascii=False, indent=2)
    return str(out_path)


def run_pipeline_step(cfg: dict[str, Any], logger) -> list[MemeCandidate]:
    """Load the news cache, match emotions, save results. Called by CLI and scheduler.py."""
    stories = load_news_cache(cfg)
    if not stories:
        logger.warning(
            f"No stories found in {cfg['paths']['news_cache_file']} - run news_scraper.py first"
        )
        return []

    candidates = match_all(stories, cfg)
    out_path = save_matched(candidates, cfg)
    logger.info(f"Matched emotions for {len(candidates)} stories -> {out_path}")
    for c in candidates:
        logger.info(f"  [{c.emotion:10s}] {c.top_caption}  ::  {c.punchline}")
    return candidates


def main() -> list[MemeCandidate]:
    cfg = load_config()
    logger = get_logger("emotion_matcher", cfg)
    return run_pipeline_step(cfg, logger)


if __name__ == "__main__":
    main()
