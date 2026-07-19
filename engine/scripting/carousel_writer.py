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
Hook to use (or write a stronger version): {topic_data['hook']}
CTA style: {pillar.get('cta_style', 'save-reflect')}

Write exactly 7 slides as a JSON array. STRICT word count rules — failure to follow = rejected:
- Slide 1 (hook): EXACTLY 8-14 words. One punchy statement. No question marks.
- Slides 2-6 (content): EXACTLY 20-50 words each. 2-4 sentences. Specific facts, names, numbers.
- Slide 7 (CTA): EXACTLY 15-30 words. Save/share directive.

NO markdown. Plain text only. No **bold**, no bullet points.

[
  {{"slide": 1, "text": "8 to 14 word hook statement here", "emoji": "⚡"}},
  {{"slide": 2, "text": "20 to 50 word content with specific fact or name or number here", "emoji": "..."}},
  {{"slide": 3, "text": "20 to 50 word content with specific fact or name or number here", "emoji": "..."}},
  {{"slide": 4, "text": "20 to 50 word content with specific fact or name or number here", "emoji": "..."}},
  {{"slide": 5, "text": "20 to 50 word content with specific fact or name or number here", "emoji": "..."}},
  {{"slide": 6, "text": "20 to 50 word content with specific fact or name or number here", "emoji": "..."}},
  {{"slide": 7, "text": "15 to 30 word save or share CTA here", "emoji": "📌"}}
]"""

    result = complete_json(_SYSTEM, user)
    # Some models wrap the array: {"slides": [...]}
    if isinstance(result, dict):
        for v in result.values():
            if isinstance(v, list):
                result = v
                break
    if not isinstance(result, list) or len(result) != 7:
        raise ValueError(f"Expected 7 slides, got {type(result)}: {result}")

    # Strip any markdown the model adds despite instructions
    import re
    for s in result:
        s["text"] = re.sub(r'\*+', '', s.get("text", "")).strip()

    return result
