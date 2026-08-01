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
from engine.ideation.watchlist import get_pillar_reference_handles

_SYSTEM = """\
You pick topics for @profit_prompts_ (AI Tools • Earning Strategies), an
Instagram page for curious 18-35 year-olds who want practical AI workflows
and honest side-income ideas.

Voice: You are NOT a teacher. You are an insider who just found something
useful and is telling a friend. First-person or imperative. Never neutral
third-person.

Rules:
- Be specific, never generic. "3 cognitive biases" is bad.
  "Why juries make wrong decisions" is good.
- Hook must create tension: challenge a belief, reveal a paradox, or
  promise a secret. Use one of 4 curiosity patterns (see hook field).
- Every fact must be accurate and verifiable. Prefer real tool names
  (Claude, ChatGPT, Perplexity, GitHub, Pinokio, Amazon, Fiverr) over
  abstract categories.
- Write plain English. No hype verbs (utilize, leverage, unlock, empower,
  discover, revolutionize). No hedging (may, might, could, sometimes).
- The angle must be counterintuitive — the thing that makes someone say
  "wait, what?" — not a Wikipedia summary.
- Return ONLY valid JSON matching the exact schema requested. No markdown
  fences.
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

    handles = get_pillar_reference_handles(pillar["id"])
    if handles:
        handle_lines = "\n".join(
            f"  - @{h['handle']}: {h.get('why','').strip().splitlines()[0]}"
            for h in handles
        )
        handles_block = f"""

REFERENCE CREATORS (audience overlap — use for TONE and TOPIC AREA only, NEVER copy):
{handle_lines}"""
    else:
        handles_block = ""

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
topic on it — use language they'd recognize from the trend, and set
"trend_source" in the JSON to the EXACT title of that trend (copy-paste from
the list above). Otherwise ignore trends, set "trend_source" to null, and
pick a fresh angle from the topic seeds. Never force a politics/news/
finance-ticker trend into an educational pillar; when in doubt, use the seeds
and null."""
        trend_source_field = '  "trend_source": "exact trend title you anchored on, or null if none used",\n'
    else:
        trend_block = ""
        trend_source_field = ""

    user = f"""Pillar: {pillar['name']} {pillar['emoji']}
Description: {pillar['description']}

Topic seeds (use as direction only, do NOT repeat verbatim):
{seeds_str}

Recently posted topics to AVOID:
{recent_str}
{handles_block}{trend_block}

Return ONE topic as JSON with exactly these keys:
{{
  "topic": "specific subject in 3-6 words",
  "angle": "the counterintuitive entry point in 1 sentence",
  "hook": "slide 1 text using ONE of these 4 curiosity patterns (8-14 words, no ? or !):
    A) insider number:      '5 free AI tools people are quietly using to make $500/month'
    B) contrarian truth:    'Most people use ChatGPT wrong. The 1% do this instead.'
    C) time-boxed win:      'How I built a personal AI assistant in 30 minutes for free'
    D) insider observation: 'Nobody talks about the ChatGPT setting that saves 90% on API bills'
    Include ONE specific number, named tool, or dollar amount. NO hype verbs
    (ditch, unlock, discover, revolutionize, unleash, empower).",
{trend_source_field}  "image_prompts": [
    "hero visual: what the topic literally shows (dark navy background, cyan and green accents, no text, editorial illustration)",
    "supporting visual: a data / chart / metaphor angle on the same topic (dark navy, no text, editorial)",
    "human context: a person / scene that grounds the topic emotionally (dark navy, cinematic, no text)"
  ],
  "dall_e_prompt": "legacy single-image fallback prompt — same as image_prompts[0]",
  "caption": "Instagram caption in insider voice (first-person or imperative, NOT teacher voice). 3-5 short sentences that expand the hook's promise with a real story or number. End with a genuine question inviting a comment. Then on a new line, 8-12 hashtags: mix 3 brand tags (#ProfitPrompts #AITools #EarningStrategies) with 5-9 topic-specific ones."
}}

Rules for image_prompts:
- EXACTLY 3 prompts, distinct visual angles on the SAME topic (not the same image).
- Every prompt must include: "dark navy background", "no text, no letters".
- Never mention brand logos or trademarked characters (FLUX cannot render them).
- Keep each prompt 15-40 words — too short trips the content filter."""

    return complete_json(_SYSTEM, user)
