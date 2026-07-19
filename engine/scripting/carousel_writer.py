"""Write all 7 carousel slides using Claude.

Slide structure:
  1: Hook — bold statement (8-14 words)
  2-6: Content slides — one insight per slide (15-55 words each)
  7: CTA — save/share call-to-action tailored to pillar style

Returns a list of 7 dicts: [{slide_number, title, body, emoji}, ...]
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
You are writing slides for an Instagram educational carousel. Each slide is a
single screen people swipe through on their phone. Rules:

SLIDE CRAFT:
- Slide 1 (hook): Bold statement that creates tension. 8-14 words. NO question marks.
  Must make the reader NEED to swipe to slide 2.
- Slides 2-6: One idea each. Lead with the most surprising sentence.
  15-55 words per slide. Never repeat information. Each slide must be a revelation.
- Slide 7 (CTA): Direct ask. "Save this" or "Share this with someone who..." + 1 line why.

WRITING STYLE:
- Short sentences. Punchy rhythm.
- Active voice. No passive.
- Concrete numbers and names over abstract claims.
- Never start two consecutive slides the same way.
- One emoji per slide maximum.
"""


def write_carousel(topic_data: dict, pillar: dict) -> list[dict]:
    """Return list of 7 slide dicts."""
    client = _get_client()

    prompt = f"""Topic: {topic_data['topic']}
Angle: {topic_data['angle']}
Pillar CTA style: {pillar.get('cta_style', 'save-reflect')}
Hook style: {pillar.get('hook_style', 'challenge-belief')}

Write exactly 7 slides as a JSON array:
[
  {{"slide": 1, "text": "...", "emoji": "🧠"}},
  {{"slide": 2, "text": "...", "emoji": "..."}},
  ...
  {{"slide": 7, "text": "...", "emoji": "..."}}
]

Slide 1 text = the hook ({topic_data['hook']}) or a stronger version of it.
Slides 2-6: develop the topic with surprising, specific facts about: {topic_data['angle']}
Slide 7: CTA matching the {pillar.get('cta_style', 'save-reflect')} style.

Return ONLY valid JSON array. No markdown, no explanation."""

    with _get_client().messages.stream(
        model="claude-opus-4-7",
        max_tokens=2048,
        thinking={"type": "adaptive"},
        system=_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        final = stream.get_final_message()

    text_parts = [b.text for b in final.content if b.type == "text"]
    raw = "".join(text_parts).strip()

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    slides = json.loads(raw)
    if not isinstance(slides, list) or len(slides) != 7:
        raise ValueError(f"Expected 7 slides, got {len(slides) if isinstance(slides, list) else type(slides)}")

    return slides
