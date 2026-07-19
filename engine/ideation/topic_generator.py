"""Generate a specific carousel topic + angle using a free LLM.

Returns a dict with: topic, angle, hook, dall_e_prompt, caption
"""
from __future__ import annotations

from engine.llm_client import complete_json

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


def generate_topic(pillar: dict, recent_topics: list[str]) -> dict:
    """Return a topic dict with keys: topic, angle, hook, dall_e_prompt, caption."""
    recent_str = "\n".join(f"  - {t}" for t in recent_topics[-10:]) or "  (none yet)"
    seeds_str = "\n".join(f"  - {s}" for s in pillar.get("topic_seeds", []))

    user = f"""Pillar: {pillar['name']} {pillar['emoji']}
Description: {pillar['description']}

Topic seeds (use as direction only, do NOT repeat verbatim):
{seeds_str}

Recently posted topics to AVOID:
{recent_str}

Return ONE topic as JSON with exactly these keys:
{{
  "topic": "specific subject in 3-6 words",
  "angle": "the counterintuitive entry point in 1 sentence",
  "hook": "slide 1 text — 8-14 words, bold statement, NO question mark",
  "dall_e_prompt": "background image for DALL-E 3, no text, dramatic lighting, 1 sentence",
  "caption": "Instagram caption, 3-5 sentences expanding the hook's promise, ends with a question for comments, then 8-12 hashtags on a new line"
}}"""

    return complete_json(_SYSTEM, user)
