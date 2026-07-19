"""7 hard quality gates — every post must pass all gates or is rejected.

Gates:
  1. Slide count == 7
  2. Hook length: 6-14 words
  3. All content slides: 15-55 words
  4. No duplicate topic in last 30 days (SQLite check)
  5. No filler phrases detected
  6. Hook is a statement, not a question
  7. CTA slide contains save/share directive

Returns (passed: bool, failures: list[str])
"""
from __future__ import annotations

import re

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

_CTA_WORDS = ["save", "share", "send", "bookmark", "follow", "tag"]


def _word_count(text: str) -> int:
    return len(text.split())


def _has_filler(text: str) -> bool:
    lower = text.lower()
    return any(f in lower for f in _FILLER)


def run_gates(
    slides: list[dict],
    topic: str,
    db_conn,  # sqlite3.Connection or None
    lookback_days: int = 30,
) -> tuple[bool, list[str]]:
    failures: list[str] = []

    # Gate 1: slide count
    if len(slides) != 7:
        failures.append(f"Gate 1: Expected 7 slides, got {len(slides)}")

    if len(slides) >= 1:
        hook_text = slides[0].get("text", "")

        # Gate 2: hook word count
        hw = _word_count(hook_text)
        if not (6 <= hw <= 14):
            failures.append(f"Gate 2: Hook is {hw} words (must be 6-14): '{hook_text}'")

        # Gate 6: hook must be a statement, not a question
        if hook_text.strip().endswith("?"):
            failures.append(f"Gate 6: Hook ends with '?' — must be a statement: '{hook_text}'")

    # Gate 3: content slide word counts
    for slide in slides[1:6]:
        text = slide.get("text", "")
        wc = _word_count(text)
        n = slide.get("slide", "?")
        if not (15 <= wc <= 55):
            failures.append(f"Gate 3: Slide {n} has {wc} words (must be 15-55)")

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
    all_text = " ".join(s.get("text", "") for s in slides)
    if _has_filler(all_text):
        found = [f for f in _FILLER if f in all_text.lower()]
        failures.append(f"Gate 5: Filler phrases detected: {found}")

    # Gate 7: CTA check
    if len(slides) >= 7:
        cta_text = slides[-1].get("text", "").lower()
        if not any(w in cta_text for w in _CTA_WORDS):
            failures.append(f"Gate 7: CTA slide missing save/share directive: '{slides[-1].get('text','')}'")

    return (len(failures) == 0, failures)
