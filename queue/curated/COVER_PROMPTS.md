# Cover + last-slide prompts

The pipeline uses `assets/curated/<post_id>/cover.jpg` for slide 1 and
`assets/curated/<post_id>/last.jpg` for slide 7 if present. Both render at
**1080×1350 (4:5)**, photo occupying the top 62%, black headline bar below.

**Workflow:** generate in the Gemini app → save as
`assets/curated/<id>/cover.jpg` and `.../last.jpg` → `git add` + push.
No cover? The template falls back to a CSS halftone field. Nothing breaks.

---

## What changed, and why

Two weeks of data now, and both point the same way.

**Photoreal covers underperform.** Week of 17–23 Aug ran photoreal documentary
covers — a desk, a laptop, a receipt. Mean reach **21.4**. The prior fortnight,
on hand-made illustrated covers, averaged **38.5**. The competitor teardown
says the same thing louder: @syntaix.ai's best cover is a glowing green marble
statue with money falling and candlestick charts. @alamin.8020ai's is a
cut-out Elon over a halftone poster field. Nobody in this niche photographs a
desk.

**The winning cover is a joke or a shock about the argument**, not an
illustration of the topic. Tech CEOs around a casket marked RIP AI
SUBSCRIPTIONS stops a thumb. A tidy desk does not.

**The last slide is a face plus a claim about the page.** Measured:

- @syntaix.ai — 3D caricature of Sam Altman, someone whispering in his ear:
  *"TRUST ME… YOU WON'T REGRET FOLLOWING THIS PAGE"*
- @stics.ai — Satya Nadella, glowing MS and Google logos:
  *"WE SHARE INTERESTING AI CONTENT YOU WON'T SEE ANYWHERE ELSE"*

Both are claims about the page, not false claims about the feed. Our slide 7
now reads **"You won't see this anywhere else / Follow @profit_prompts_"**.

**No comment bait this week.** All fourteen captions last week opened with
"Comment WORD" — comments rose 6.5× and reach fell 44%. Instagram's guidelines
name engagement bait explicitly. Dropped.

---

## Rules for every prompt

1. **Cinematic 3D rendered illustration.** Glossy, saturated, dramatically lit.
   Not *photograph*, not *editorial illustration* — that second phrase is what
   produced the generic look in early August.
2. **A physical metaphor for the argument**, staged as a scene. Chains on a
   microphone. A mousetrap baited with a credit card. A dark gap on a lit globe.
3. **Subject in the upper two thirds.** The bar covers the bottom 38%.
4. **One dominant colour**, stated explicitly.
5. **No text, no logos, no watermarks.** The template adds all type.
6. **Cover and last slide should rhyme.** Same world, opposite state — chained
   microphone on the cover, chains fallen away on the last. It reads as a
   bookend, which is what stops a CTA slide feeling like an ad.
7. **4:5 portrait**, 1080×1350 or larger.

### On caricatures of real people
@syntaix.ai and @stics.ai both do it. Keep it **obviously absurd** — funerals,
cartoon scale, physical impossibility. A *plausible* rendered image of a real
person doing something they did not do is the version that draws a report.

---

## Week of Wed 26 Aug → Tue 1 Sep 2026

Morning slot only (11:00 IST). The night slot is now a Reel.

| Slot | Topic | Cover prompt | Last-slide prompt |
|---|---|---|---|
| `20260826_05` | Robot ran the 400m in 45.66s | Cinematic 3D rendered illustration, a sleek white humanoid robot mid-sprint on a blue athletics track with an absurdly exaggerated running posture, motion blur streaking behind it, stadium floodlights, dramatic low angle, hyper-saturated blue and white palette, glossy render, subject in upper two thirds, no text | Cinematic 3D rendered illustration, the same white humanoid robot standing on an Olympic podium wearing a gold medal, arms raised in an awkwardly stiff victory pose, confetti falling, dramatic rim lighting, dark background, glossy render, upper two thirds, no text |
| `20260827_05` | Open video models caught the paid ones | Cinematic 3D rendered illustration, two identical film projectors facing each other on a dark stage, one gleaming gold and chained shut with a heavy padlock, the other plain steel and wide open with light pouring out, dramatic single-source lighting, deep shadows, saturated amber palette, glossy render, upper two thirds, no text | Cinematic 3D rendered illustration, a giant open padlock rendered in gold sitting on a dark reflective surface with light streaming through the shackle, dramatic rim lighting, hyper-saturated amber and black, glossy render, upper two thirds, no text |
| `20260828_05` | Training a model costs $200k | Cinematic 3D rendered illustration, an enormous stack of server racks shaped like a mountain with a tiny businessman in a suit standing at the base looking up, dramatic backlighting, cold blue server LEDs, heavy atmospheric haze, extreme scale contrast, glossy render, upper two thirds, no text | Cinematic 3D rendered illustration, a single glowing GPU card resting on a velvet cushion under a museum spotlight behind glass, dark gallery background, dramatic single-source lighting, saturated blue, glossy render, upper two thirds, no text |
| `20260829_05` | Most "free" AI tools are not free | Cinematic 3D rendered illustration, a giant glowing FREE sign made of neon hanging above a mousetrap holding a credit card as bait, dark warehouse setting, dramatic single-source lighting from the neon, hyper-saturated pink and cyan, deep shadows, glossy render, upper two thirds, no text | Cinematic 3D rendered illustration, a hand holding a magnifying glass over a contract covered in tiny illegible print, one clause glowing red through the lens, dark desk, dramatic side lighting, saturated red and black, glossy render, upper two thirds, no text |
| `20260830_05` | Voice cloning is a licence problem | Cinematic 3D rendered illustration, a vintage microphone wrapped in heavy iron chains with a legal wax seal stamped on the chain, dark studio background, single dramatic overhead spotlight, deep shadows, saturated red and gold, glossy render, upper two thirds, no text | Cinematic 3D rendered illustration, the same vintage microphone with the chains fallen away in a heap and glowing warm light spilling from the microphone head, dark studio, dramatic rim lighting, saturated gold, glossy render, upper two thirds, no text |
| `20260831_05` | What Indian creators can build | Cinematic 3D rendered illustration, a world globe made of glowing circuitry with the Indian subcontinent rendered as a dark unlit gap while every other region blazes with light, dark space background, dramatic rim lighting, saturated blue and orange, glossy render, upper two thirds, no text | Cinematic 3D rendered illustration, the same circuitry globe with the Indian subcontinent now blazing brightest of all in warm gold, light spreading outward from it, dark space background, dramatic glow, glossy render, upper two thirds, no text |
| `20260901_05` | What shipped in AI this week | Cinematic 3D rendered illustration, five glowing monoliths of different heights standing in a dark desert under a stormy sky, the tallest one blazing with light while the others are dim, dramatic backlighting, heavy atmospheric haze, saturated teal and orange, glossy render, upper two thirds, no text | Cinematic 3D rendered illustration, a lone figure in silhouette walking toward the single brightest monolith across dark sand, the other four fading behind, dramatic backlighting, atmospheric haze, saturated teal, glossy render, upper two thirds, no text |

Every pair rhymes: chained then unchained, dark gap then blazing, mountain then
single artefact. That bookend is deliberate.

⚠️ **`20260826_05` is news-pegged.** The 45.66s time and the Tiangong Omni name
come from a competitor's caption, not a primary source. Verify before it goes
out tomorrow morning.
