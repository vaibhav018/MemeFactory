"""Generate a specific carousel topic + angle using Claude.

Given a pillar config, Claude returns:
  - topic: specific subject (not generic)
  - angle: the counterintuitive / mind-blowing entry point
  - hook: slide-1 text (6-14 words, high shareability)
  - dall_e_prompt: background image description for DALL-E 3
  - caption: Instagram caption with hashtags

Uses adaptive thinking + streaming for quality output.
"""
from __future__ import annotations

import json
import os
import sys

import anthropic

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            sys.exit("ANTHROPIC_API_KEY not set")
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


_SYSTEM = """\
You are a world-class Instagram content strategist for a "Modern Mastery" education page.
Your content targets curious 18-35 year-olds globally. The 2026 Instagram algorithm
rewards SAVES and SHARES above all else — write content people will bookmark and
forward to friends.

Rules:
- Be specific, never generic. "3 cognitive biases" → bad. "Why juries make wrong decisions" → good.
- Hook must create a tension: challenge a belief, reveal a paradox, or promise a secret.
- Every fact must be accurate and verifiable.
- Write in plain English. No jargon. No filler phrases like "it's important to note".
- The angle must be counterintuitive — the thing that makes someone say "wait, what?"
"""


def generate_topic(pillar: dict, recent_topics: list[str]) -> dict:
    """Return a topic dict with keys: topic, angle, hook, dall_e_prompt, caption."""
    client = _get_client()

    recent_str = "\n".join(f"  - {t}" for t in recent_topics[-10:]) or "  (none yet)"
    seeds_str = "\n".join(f"  - {s}" for s in pillar.get("topic_seeds", []))

    prompt = f"""Pillar: {pillar['name']} {pillar['emoji']}
Pillar description: {pillar['description']}

Topic seeds for inspiration (do NOT repeat these verbatim — use as direction only):
{seeds_str}

Recently posted topics to AVOID:
{recent_str}

Generate ONE specific carousel topic in this exact JSON format:
{{
  "topic": "specific subject in 3-6 words",
  "angle": "the counterintuitive entry point in 1 sentence",
  "hook": "slide 1 text — 8-14 words, creates urgency/curiosity, no question marks",
  "dall_e_prompt": "photorealistic/abstract background image for DALL-E 3, no text, dramatic lighting, matches pillar mood. 1 sentence.",
  "caption": "Instagram caption, 3-5 sentences. Expand the hook's promise. End with a question to drive comments. Include 8-12 relevant hashtags on a new line."
}}

Return ONLY valid JSON. No markdown fences, no explanation."""

    content_blocks = []
    with client.messages.stream(
        model="claude-opus-4-7",
        max_tokens=1024,
        thinking={"type": "adaptive"},
        system=_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for block in stream:
            pass
        final = stream.get_final_message()

    for block in final.content:
        if block.type == "text":
            content_blocks.append(block.text)

    raw = "".join(content_blocks).strip()
    # strip markdown fences if model adds them anyway
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    return json.loads(raw)
