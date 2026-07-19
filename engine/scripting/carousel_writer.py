"""Write all 7 carousel slides using a free LLM.

Returns a list of 7 dicts: [{slide, text, emoji}, ...]
"""
from __future__ import annotations

from engine.llm_client import complete_json

_SYSTEM = """\
You write slides for an Instagram educational carousel. Each slide is a single screen
people swipe on their phone.

SLIDE STRUCTURE:
- Slide 1 (hook): Bold statement creating tension. 8-14 words. NO question marks.
  Must make the reader NEED to swipe to slide 2.
- Slides 2-6: One idea each. Lead with the most surprising sentence.
  15-55 words per slide. Never repeat information. Each slide is a revelation.
- Slide 7 (CTA): Direct ask — "Save this" or "Share this with someone who..." + 1 line why.

WRITING STYLE:
- Short sentences. Punchy rhythm.
- Active voice. No passive.
- Concrete numbers and names, not abstract claims.
- Never start two consecutive slides the same way.
- One emoji per slide maximum.

Return ONLY a valid JSON array. No markdown fences, no explanation.
"""


def write_carousel(topic_data: dict, pillar: dict) -> list[dict]:
    """Return list of 7 slide dicts."""
    user = f"""Topic: {topic_data['topic']}
Angle: {topic_data['angle']}
Hook to use (or improve): {topic_data['hook']}
CTA style: {pillar.get('cta_style', 'save-reflect')}

Write exactly 7 slides as a JSON array:
[
  {{"slide": 1, "text": "...", "emoji": "🧠"}},
  {{"slide": 2, "text": "...", "emoji": "..."}},
  {{"slide": 3, "text": "...", "emoji": "..."}},
  {{"slide": 4, "text": "...", "emoji": "..."}},
  {{"slide": 5, "text": "...", "emoji": "..."}},
  {{"slide": 6, "text": "...", "emoji": "..."}},
  {{"slide": 7, "text": "...", "emoji": "..."}}
]

Slide 1 = the hook.
Slides 2-6 = develop the angle with specific, surprising facts.
Slide 7 = CTA in the {pillar.get('cta_style', 'save-reflect')} style."""

    result = complete_json(_SYSTEM, user)
    if not isinstance(result, list) or len(result) != 7:
        raise ValueError(f"Expected 7 slides, got {type(result)}: {result}")
    return result
