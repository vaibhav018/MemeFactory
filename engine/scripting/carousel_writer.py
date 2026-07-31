"""Write all 7 carousel slides using a free LLM.

Returns a list of 7 dicts: [{slide, text, emoji}, ...]
"""
from __future__ import annotations

from engine.llm_client import complete_json

_SYSTEM = """\
You write slides for an Instagram educational carousel for @profit_prompts_
("AI Tools • Earning Strategies"). Each slide is a single screen people
swipe on their phone.

READING LEVEL (STRICT) — a 12-year-old should understand every sentence:
- Maximum 10 words per sentence. Break longer thoughts into two sentences.
- Use plain, everyday words. If a technical term is unavoidable, put a
  short plain-English explanation right after it in parentheses.
  Good: "prompt caching (a way to reuse old answers)"
  Bad:  "leverage prompt caching mechanisms"
- One idea per sentence. No commas stacking multiple concepts.
- Concrete numbers and real names, not abstract claims.
- Active voice. Present tense when possible.
- Never start two slides the same way.

BANNED WORDS (rejected automatically — never use):
utilize, leverage, paradigm, synergy, robust, seamless, holistic,
disrupt, empower, unlock, unleash, revolutionize, streamline,
optimize, methodology, framework (as a buzzword), ecosystem (as
a buzzword), transformative, cutting-edge, next-level, game-changer,
best-in-class, world-class, mission-critical, thought-leader.

BAD:  "Leverage prompt caching to unlock cost optimization."
GOOD: "Prompt caching saves 90% of your bill. It reuses old answers."

SLIDE STRUCTURE:
- Slide 1 (hook): Bold statement creating tension. 8-14 words. NO question marks.
  Must make the reader NEED to swipe to slide 2.
- Slides 2-6: One idea each. Lead with the most surprising sentence.
  15-55 words per slide. Never repeat information. Each slide is a fact
  or a step, not fluff.
- Slide 7 (CTA): Direct ask — "Save this" or "Share this with someone who..." + 1 short line why.

- One emoji per slide maximum.

Return ONLY a valid JSON array. No markdown fences, no explanation.
"""


_SPLIT_ELIGIBLE_PILLARS = {"ai_tools_workflows", "wealth_hustles"}


def write_carousel(topic_data: dict, pillar: dict) -> list[dict]:
    """Return list of 7 slide dicts."""

    split_block = ""
    if pillar.get("id") in _SPLIT_ELIGIBLE_PILLARS:
        split_block = """

OPTIONAL SPLIT-SCREEN LAYOUT (only for slides 2-6, and ONLY if the point is a
natural side-by-side comparison — Free vs Paid, Myth vs Reality, Old vs New,
Wrong vs Right, Beginner vs Pro). Use it for AT MOST 2 of the 5 content slides.
Do NOT force it; if the point isn't a comparison, use the normal single-text slide.

When you use it, that slide's JSON object uses this shape instead:
  {"slide": N, "layout": "split", "emoji": "...",
   "left_label": "1-3 UPPERCASE words (e.g. FREE, MYTH, OLD WAY)",
   "left_text":  "12-28 words — concrete, specific, one fact",
   "right_label": "1-3 UPPERCASE words (e.g. PAID, REALITY, NEW WAY)",
   "right_text": "12-28 words — concrete, specific, one fact"}
Left and right must contrast on the SAME dimension. No "text" field on split slides.
"""

    user = f"""Topic: {topic_data['topic']}
Angle: {topic_data['angle']}
Hook to use (or write a stronger version): {topic_data['hook']}
Pillar: {pillar.get('id')}
CTA style: {pillar.get('cta_style', 'save-reflect')}

Write exactly 7 slides as a JSON array. STRICT word count rules — failure to follow = rejected:
- Slide 1 (hook): EXACTLY 8-14 words. One punchy statement. No question marks.
- Slides 2-6 (content): EXACTLY 20-50 words each. 2-4 sentences. Specific facts, names, numbers.
- Slide 7 (CTA): EXACTLY 15-30 words. Save/share directive.

NO markdown. Plain text only. No **bold**, no bullet points.
{split_block}
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
        for key in ("text", "left_label", "left_text", "right_label", "right_text"):
            if key in s and isinstance(s[key], str):
                s[key] = re.sub(r'\*+', '', s[key]).strip()

    return result
