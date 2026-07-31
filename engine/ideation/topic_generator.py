"""Generate a specific carousel topic + angle using a free LLM.

Returns a dict with: topic, angle, hook, dall_e_prompt, caption.

For pillars wired to trend sources (see engine.trends.fetch._PILLAR_SOURCES),
the current top-N trending items are injected into the prompt so Claude can
anchor the topic on something people are actually searching/reading TODAY
rather than generating from imagination alone. Evergreen pillars get no
trend injection -- their seeds are already good.
"""
from __future__ import annotations

from engine.llm_client import complete_json
from engine.trends.fetch import get_pillar_candidates

_SYSTEM = """\
You are a world-class Instagram content strategist for a "Modern Mastery" education page.
Your content targets curious 18-35 year-olds globally. The Instagram algorithm rewards
SAVES and SHARES above all else — write content people will bookmark and forward.

Rules:
- Be specific, never generic. "3 cognitive biases" is bad. "Why juries make wrong decisions" is good.
- Hook must create tension: challenge a belief, reveal a paradox, or promise a secret.
- Every fact must be accurate and verifiable.
- Write plain English. No jargon. No filler like "it's important to note".
- The angle must be counterintuitive — the thing that makes someone say "wait, what?"
- Return ONLY valid JSON matching the exact schema requested. No markdown fences.
"""


def _fetch_trend_candidates(pillar_id: str, limit: int = 8) -> list[dict]:
    """Wrapped in try/except so a fetch outage never blocks ideation."""
    try:
        return get_pillar_candidates(pillar_id, limit=limit)
    except Exception:
        return []


def generate_topic(pillar: dict, recent_topics: list[str]) -> dict:
    """Return a topic dict with keys: topic, angle, hook, dall_e_prompt, caption."""
    recent_str = "\n".join(f"  - {t}" for t in recent_topics[-10:]) or "  (none yet)"
    seeds_str = "\n".join(f"  - {s}" for s in pillar.get("topic_seeds", []))

    trends = _fetch_trend_candidates(pillar["id"])
    if trends:
        trend_lines = "\n".join(
            f"  - [{t['source']}] {t['title']}" for t in trends
        )
        trend_block = f"""

TRENDING NOW (last 24-48h, mixed signal — some will fit the pillar, some won't):
{trend_lines}

If ONE of the trending items above is a natural fit for this pillar's audience
(curious 18-35 year-olds who save/share educational carousels), anchor your
topic on it — use language they'd recognize from the trend. Otherwise ignore
trends entirely and pick a fresh angle from the topic seeds. Never force a
politics/news/finance-ticker trend into an educational pillar; when in doubt,
use the seeds."""
    else:
        trend_block = ""

    user = f"""Pillar: {pillar['name']} {pillar['emoji']}
Description: {pillar['description']}

Topic seeds (use as direction only, do NOT repeat verbatim):
{seeds_str}

Recently posted topics to AVOID:
{recent_str}
{trend_block}

Return ONE topic as JSON with exactly these keys:
{{
  "topic": "specific subject in 3-6 words",
  "angle": "the counterintuitive entry point in 1 sentence",
  "hook": "slide 1 text — 8-14 words, bold statement, NO question mark",
  "dall_e_prompt": "background image for DALL-E 3, no text, dramatic lighting, 1 sentence",
  "caption": "Instagram caption, 3-5 sentences expanding the hook's promise, ends with a question for comments, then 8-12 hashtags on a new line"
}}"""

    return complete_json(_SYSTEM, user)
