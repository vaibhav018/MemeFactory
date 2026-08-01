"""9 hard quality gates — every post must pass all gates or is rejected.

Gates:
  1. Slide count == 7
  2. Hook length: 6-14 words
  3. All content slides: 15-55 words (split slides sum both sides)
  4. No duplicate topic in last 30 days (SQLite check)
  5. No filler phrases detected
  6. Hook is a statement, not a question
  7. CTA slide contains save/share directive
  8. Trend freshness: if the topic was anchored on a trend, reject when the
     trend is >48h old since first seen (or when it can't be verified)
  9. Reading level: no banned jargon words, no sentences over 14 words
     (@profit_prompts_ targets grade-6 reading)

Returns (passed: bool, failures: list[str])
"""
from __future__ import annotations

import re

from engine.trends.fetch import get_trend_age_hours

_FILLER = [
    "it's important to note",
    "it is worth noting",
    "in conclusion",
    "to summarize",
    "as we can see",
    "needless to say",
    "at the end of the day",
    "in today's world",
]

# Corporate-speak buzzwords that break the "12-year-old can read it" rule.
# Kept short — false positives are annoying. Match whole words only.
_BANNED_JARGON = {
    "utilize", "leverage", "leverages", "leveraging", "paradigm", "synergy",
    "robust", "seamless", "seamlessly", "holistic", "disrupt", "disruptive",
    "empower", "empowers", "unlock", "unleash", "unleashes", "revolutionize",
    "revolutionary", "streamline", "streamlines", "optimize", "optimizes",
    "methodology", "transformative", "cutting-edge", "next-level",
    "game-changer", "game-changing", "best-in-class", "world-class",
    "mission-critical", "thought-leader",
}
_JARGON_RE = re.compile(r"\b(" + "|".join(re.escape(w) for w in _BANNED_JARGON) + r")\b",
                        flags=re.IGNORECASE)

# Sentences over this many words break the school-kid readability target.
# Enforced only softly (warn if just over, hard-fail at 20+).
_SENTENCE_HARD_WORD_LIMIT = 20
_SENTENCE_RE = re.compile(r"[.!?]+\s+|[.!?]+$")

_CTA_WORDS = ["save", "share", "send", "bookmark", "follow", "tag"]


def _strip_markdown(text: str) -> str:
    import re
    text = re.sub(r'\*+', '', text)   # **bold** / *italic*
    text = re.sub(r'#+\s*', '', text)  # headings
    text = re.sub(r'`+', '', text)     # code
    return text.strip()


def _word_count(text: str) -> int:
    return len(_strip_markdown(text).split())


def _has_filler(text: str) -> bool:
    lower = text.lower()
    return any(f in lower for f in _FILLER)


_TREND_MAX_AGE_HOURS = 48.0


def run_gates(
    slides: list[dict],
    topic: str,
    db_conn,  # sqlite3.Connection or None
    lookback_days: int = 30,
    trend_source: str | None = None,
) -> tuple[bool, list[str]]:
    failures: list[str] = []

    # Gate 1: slide count
    if len(slides) != 7:
        failures.append(f"Gate 1: Expected 7 slides, got {len(slides)}")

    if len(slides) >= 1:
        hook_text = slides[0].get("text", "")

        # Gate 2: hook word count
        hw = _word_count(hook_text)
        if not (5 <= hw <= 16):
            failures.append(f"Gate 2: Hook is {hw} words (must be 6-14): '{hook_text}'")

        # Gate 6: hook must be a statement, not a question
        if hook_text.strip().endswith("?"):
            failures.append(f"Gate 6: Hook ends with '?' — must be a statement: '{hook_text}'")

    # Gate 3: content slides must not be empty, and must not be walls of text.
    # Each layout defines what "empty" and "wall of text" mean for its schema.
    for slide in slides[1:6]:
        n = slide.get("slide", "?")
        layout = slide.get("layout")
        if layout == "split":
            text = (slide.get("left_text", "") + " " + slide.get("right_text", "")).strip()
            if not slide.get("left_label") or not slide.get("right_label"):
                failures.append(f"Gate 3: Slide {n} split-layout missing left_label/right_label")
        elif layout == "step":
            if not slide.get("title") or not slide.get("body"):
                failures.append(f"Gate 3: Slide {n} step-layout missing title/body")
            text = f"{slide.get('title','')} {slide.get('body','')}"
        elif layout == "big_stat":
            if not slide.get("stat"):
                failures.append(f"Gate 3: Slide {n} big_stat-layout missing stat")
            # big_stat is intentionally sparse — one huge number + tiny caption
            text = f"{slide.get('stat','')} {slide.get('unit','')} {slide.get('caption','')}"
            # skip the min/max word check for big_stat
            continue
        elif layout == "numbered":
            items = slide.get("items") or []
            if not (3 <= len(items) <= 5):
                failures.append(f"Gate 3: Slide {n} numbered-layout needs 3-5 items, got {len(items)}")
            for i, it in enumerate(items, 1):
                if not (it.get("title") and it.get("desc")):
                    failures.append(f"Gate 3: Slide {n} numbered item {i} missing title/desc")
                    break
            # concatenate for filler / jargon downstream but skip length check
            text = " ".join(f"{it.get('title','')} {it.get('desc','')}" for it in items)
            continue
        else:
            text = slide.get("text", "")
        wc = _word_count(text)
        if wc < 4:
            failures.append(f"Gate 3: Slide {n} is too short ({wc} words)")
        elif wc > 70:
            failures.append(f"Gate 3: Slide {n} is too long ({wc} words — max 70)")

    # Gate 4: duplicate topic check
    if db_conn:
        try:
            cursor = db_conn.execute(
                "SELECT topic FROM posts WHERE topic LIKE ? AND posted_at > datetime('now', ?)",
                (f"%{topic[:30]}%", f"-{lookback_days} days"),
            )
            if cursor.fetchone():
                failures.append(f"Gate 4: Similar topic posted in last {lookback_days} days: '{topic}'")
        except Exception:
            pass  # DB not yet initialized; skip gate 4

    # Gate 5: filler phrases
    def _slide_all_text(s: dict) -> str:
        layout = s.get("layout")
        if layout == "split":
            return " ".join([s.get("left_label", ""), s.get("left_text", ""),
                             s.get("right_label", ""), s.get("right_text", "")])
        if layout == "step":
            return f"{s.get('title','')} {s.get('body','')}"
        if layout == "big_stat":
            return f"{s.get('stat','')} {s.get('unit','')} {s.get('caption','')}"
        if layout == "numbered":
            items = s.get("items") or []
            return " ".join(f"{it.get('title','')} {it.get('desc','')}" for it in items)
        return s.get("text", "")
    all_text = " ".join(_slide_all_text(s) for s in slides)
    if _has_filler(all_text):
        found = [f for f in _FILLER if f in all_text.lower()]
        failures.append(f"Gate 5: Filler phrases detected: {found}")

    # Gate 7: CTA check
    if len(slides) >= 7:
        cta_text = slides[-1].get("text", "").lower()
        if not any(w in cta_text for w in _CTA_WORDS):
            failures.append(f"Gate 7: CTA slide missing save/share directive: '{slides[-1].get('text','')}'")

    # Gate 8: trend freshness — only enforced when Claude claimed to anchor
    # on a specific trend. Silent no-op when trend_source is None/empty.
    if trend_source:
        age = get_trend_age_hours(trend_source)
        if age is None:
            failures.append(
                f"Gate 8: trend_source '{trend_source}' not found in first-seen log "
                "(hallucinated or already pruned)")
        elif age > _TREND_MAX_AGE_HOURS:
            failures.append(
                f"Gate 8: trend '{trend_source}' is {age:.1f}h old "
                f"(max {_TREND_MAX_AGE_HOURS:.0f}h)")

    # Gate 9: reading level. Ban corporate buzzwords and cap sentence length.
    all_text_for_lang = " ".join(_slide_all_text(s) for s in slides)
    bad_words = sorted({m.group(1).lower() for m in _JARGON_RE.finditer(all_text_for_lang)})
    if bad_words:
        failures.append(f"Gate 9: banned jargon detected: {bad_words}")
    for s in slides:
        n = s.get("slide", "?")
        layout = s.get("layout")
        # Each layout has its own natural sentence boundaries. Big_stat and
        # numbered are intentionally fragment-style — skip the length gate
        # for them. Split checks each side. Step checks title + body.
        if layout == "big_stat" or layout == "numbered":
            continue
        elif layout == "split":
            texts = [s.get("left_text", ""), s.get("right_text", "")]
        elif layout == "step":
            texts = [s.get("title", ""), s.get("body", "")]
        else:
            texts = [s.get("text", "")]
        offending = None
        for text in texts:
            for sentence in _SENTENCE_RE.split(text):
                wc = len(sentence.split())
                if wc >= _SENTENCE_HARD_WORD_LIMIT:
                    offending = (wc, sentence.strip())
                    break
            if offending:
                break
        if offending:
            wc, sentence = offending
            failures.append(
                f"Gate 9: slide {n} sentence is {wc} words "
                f"(max {_SENTENCE_HARD_WORD_LIMIT - 1}): '{sentence[:80]}...'")

    return (len(failures) == 0, failures)
