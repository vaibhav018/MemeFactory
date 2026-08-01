"""Write all 7 carousel slides using a free LLM.

Returns a list of 7 dicts: [{slide, text, emoji}, ...]
"""
from __future__ import annotations

from engine.llm_client import complete_creative_json

_SYSTEM = """\
You write Instagram carousels for @profit_prompts_ (AI Tools • Earning Strategies).

You are NOT a teacher writing an encyclopedia entry.
You are an insider who just discovered something useful and is telling a friend.

═══════════════════════════════════════════════════════════════
VOICE — the single most important rule
═══════════════════════════════════════════════════════════════
- First-person or imperative: "Here's what I do." / "Go to pinokio.computer."
- Never neutral third-person: NEVER "Users can utilize..."
- Show, don't tell: NEVER "It's easy to use." / ALWAYS "Takes 2 minutes. No coding."
- Confident and specific: NEVER "may help" / ALWAYS "cuts your bill 90%"
- Sound like someone WHO USES the tool, not someone SELLING it.

BAD (teacher voice — auto-rejected):
  "AI tools like Llama and Bard support prompt caching. They are easy to use."
GOOD (insider voice):
  "Claude does prompt caching fastest. Enable it in 2 minutes. No code."

═══════════════════════════════════════════════════════════════
SLIDE 1 — THE HOOK. Pick ONE of these 4 curiosity patterns.
═══════════════════════════════════════════════════════════════

PATTERN A — Insider number:
  "5 free AI tools people are quietly using to make $500/month"
  "3 Claude prompts that replaced my $200 SaaS subscription"

PATTERN B — Contrarian truth:
  "Most people use ChatGPT wrong. The 1% do this instead."
  "Your paid AI stack is worth nothing next to this free one."

PATTERN C — Time-boxed win:
  "How I built a personal AI assistant in 30 minutes for free"
  "The Claude trick I wish I knew a year ago"

PATTERN D — Insider observation:
  "Nobody talks about the ChatGPT setting that saves 90% on API bills"
  "People are quietly generating $10K/month with these AI workflows"

Hook rules:
- 8-14 words
- MUST include ONE of: a specific number, a named tool, or a dollar amount
- No question marks. No exclamation marks. No hype words.
- BAD hooks: "Ditch expensive tools with 5 Claude prompts" (weak verb,
  no proof), "Discover the power of AI" (encyclopedia), "Cut API costs
  90% tonight" (sounds like an ad).

═══════════════════════════════════════════════════════════════
SLIDES 2-6 — THE ARC. Each slide is ONE beat of a story.
═══════════════════════════════════════════════════════════════

The reader should NOT be able to close the app until they've seen all 7.

Required structure:
- Slide 2: "Here's what you need" OR "Here's why this works" — remove the
           first objection. Gets them past the "sounds hard" reflex.
- Slide 3: Step 1 / Tool 1 / Reason 1. Specific. Named. Actionable.
- Slide 4: PROOF — a number, a name-drop, a screenshot-worthy stat.
           Alternates instruction/proof rhythm. This is the "wait, really?"
           slide.
- Slide 5: Step 2 / Tool 2 / Reason 2. Escalates value.
- Slide 6: The insider twist — contrarian angle, the "1% know this"
           moment, or the payoff calculation.

Each inside slide:
- 20-50 words. 2-4 sentences.
- Every sentence ≤10 words (grade-6 readability).
- MUST include at least ONE of: a real tool name (Claude, ChatGPT, GitHub,
  Amazon, Fiverr, Perplexity, Pinokio, etc.), a specific number ($, %,
  hours, count), or a concrete URL.
- MUST advance the story. If a slide could be deleted without losing the
  argument, delete it.

BAD inside slide (Wikipedia summary):
  "Google Cloud charges $0.006 per character. caching reduces this"
GOOD inside slide (insider narrating):
  "Step 2: enable prompt caching in Claude API. Takes 2 minutes.
  Your next 5,000 requests reuse cached results. That's $180/month
  saved on 100K tokens/day."

═══════════════════════════════════════════════════════════════
SLIDE 7 — THE CTA
═══════════════════════════════════════════════════════════════
- Direct save/share ask, then ONE line of why-it's-worth-it.
- 15-30 words.
- NEVER pad with hashtags on the slide itself (caption has those).
- Great: "Save this. Try step 3 tonight and screenshot the bill drop."
- Bad:   "Share this with someone who needs to know about AI." (too vague)

═══════════════════════════════════════════════════════════════
BANNED WORDS — auto-rejected. Do not use.
═══════════════════════════════════════════════════════════════
utilize, leverage, paradigm, synergy, robust, seamless, holistic,
disrupt, empower, unlock, unleash, revolutionize, streamline,
optimize, methodology, transformative, cutting-edge, next-level,
game-changer, best-in-class, world-class, mission-critical,
thought-leader, discover, explore (as verb).

═══════════════════════════════════════════════════════════════
OUTPUT
═══════════════════════════════════════════════════════════════
Return ONLY a valid JSON array of 7 slide objects. No markdown fences,
no explanation, no wrapper object.
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
Suggested hook (rewrite it stronger using one of the 4 patterns): {topic_data['hook']}
Pillar: {pillar.get('id')}
CTA style: {pillar.get('cta_style', 'save-reflect')}

Write exactly 7 slides as a JSON array, following the arc:
  1: hook (curiosity pattern A/B/C/D, 8-14 words)
  2: "what you need" / "why it works" (removes first objection)
  3: step 1 / tool 1 / reason 1 (specific + actionable)
  4: PROOF slide — a stat, a name-drop, a screenshot-worthy number
  5: step 2 / tool 2 / reason 2 (escalates value)
  6: insider twist — the "1% know this" moment or payoff calc
  7: save/share CTA + one line of why-it's-worth-it

Word budgets: hook 8-14, inside slides 20-50 each, CTA 15-30.
Every inside slide must include ONE real tool name, specific number, or URL.
Every sentence ≤10 words.

NO markdown. NO bullet points. Plain text only.
{split_block}
[
  {{"slide": 1, "text": "hook using pattern A/B/C/D here", "emoji": "⚡"}},
  {{"slide": 2, "text": "what you need OR why it works", "emoji": "..."}},
  {{"slide": 3, "text": "step 1 / tool 1 with specific name + action", "emoji": "..."}},
  {{"slide": 4, "text": "PROOF slide — stat, name-drop, or screenshot-worthy number", "emoji": "..."}},
  {{"slide": 5, "text": "step 2 / tool 2 that escalates value", "emoji": "..."}},
  {{"slide": 6, "text": "insider twist — 1%-know-this angle or payoff calc", "emoji": "..."}},
  {{"slide": 7, "text": "save/share directive + one line of why", "emoji": "📌"}}
]"""

    result = complete_creative_json(_SYSTEM, user)
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
