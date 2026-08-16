# Cover-image prompts — user-generated Gemini covers

The pipeline auto-uses `assets/curated/<post_id>/cover.jpg` (or `.jpeg`/`.png`)
as the slide-1 photo panel. Since 2026-08-16 the template renders **1080×1350
(4:5)** with the photo occupying the **top 62%** and a black headline bar
across the bottom 38%.

**Workflow**
1. Generate the cover in the Gemini app using the prompt below.
2. Save as `assets/curated/<post_id>/cover.jpg`.
3. `git add` + `git push` — the next cron slot picks it up.

No cover? The template falls back to a CSS halftone poster field. Nothing breaks.

---

## Why the old prompts failed

Every prompt in the previous version of this file was the same sentence with
the noun swapped:

> *"minimalist editorial illustration of X, dark navy background, cyan and green
> accents, glowing circuit patterns, no text, professional"*

That template **is** the generic-AI look. "Editorial illustration" plus "glowing
circuit patterns" is the single most over-produced image in the category, and it
is why the posts read as stock.

A 133-cover scrape of 13 competitors (16 Aug 2026) shows nobody in this niche
uses generated illustration. They use **photographs and real screen captures**:

| What they actually use | Seen on |
|---|---|
| A real person, chest-up, direct gaze | @askgpts, @alamin.8020ai |
| A documentary moment with cinematic light | @stics.ai |
| A screenshot of the actual app as evidence | @evolving.ai |
| Cut-out subject over a halftone poster field | @alamin.8020ai |
| Split-screen of two real captures | @coderss_world, @evolving.ai |

Deliberately imperfect screen-grab quality outperforms polish. @coderss_world's
44k-engagement cover is two blurry phone-camera stills side by side.

---

## The rules (apply to every prompt)

1. **Photoreal, never illustrated.** Say *photograph*, *press photo*, *screen
   capture*, *shot on 35mm*. Never *illustration*, *render*, *digital art*,
   *concept art*.
2. **Keep the subject in the upper 60%.** The bottom 38% is covered by the
   headline bar. A centred subject gets its chin cut off.
3. **One specific action, not a concept.** "A man staring at a laptop at 2am in
   a dark kitchen" beats "productivity workflow".
4. **One dominant colour.** Not "cyan and green accents with gold highlights".
5. **No text, no logos, no watermarks, no UI chrome** — the template adds all type.
6. **4:5 portrait**, 1080×1350 or larger.

## The four archetypes

- **A · PORTRAIT** — one person chest-up, direct eye contact, shallow depth of
  field, single hard light. Highest stopping power; use for anything involving a
  named person or a strong claim.
- **B · DOCUMENTARY** — a real moment, natural or practical light, slight
  imperfection. Use for "someone did X" stories.
- **C · SCREEN EVIDENCE** — a device held in real hands showing a plausible
  interface, shot over the shoulder. Use for tool and how-to posts.
- **D · POSTER COMPOSITE** — desaturated cut-out subject over a high-saturation
  halftone field. Use for money/hustle posts.

---

## Week of Mon 17 → Sun 23 Aug 2026

Slots are `YYYYMMDD_HH`, `05` = 11:00 IST, `14` = 19:30 IST. Highlight words for
the headline are marked with `*asterisks*` — the template colours them yellow.

| Slot | Topic | Arch. | Cover prompt |
|---|---|---|---|
| `20260817_05` | 5 free AI tools that replaced paid apps | C | Over-the-shoulder photograph of a person at a cluttered desk holding a phone showing a grid of app icons, warm desk lamp as the only light source, deep shadows, shot on 35mm, shallow depth of field, subject in upper two thirds, no text |
| `20260817_14` | What people built with Grok 4.6 in 48 hours | B | Documentary photograph of a young developer in a dark room lit only by a large monitor showing a colourful 3D scene, face turned toward the screen in profile, magenta screen glow as the single colour, visible grain, upper two thirds, no text |
| `20260818_05` | Free Stanford + Google AI certifications | A | Portrait photograph of a student in a university corridor, backpack on one shoulder, looking directly into the lens with a slight smile, hard window light from the left, warm neutral background thrown out of focus, chest-up, upper two thirds, no text |
| `20260818_14` | OpenAI charges $80 to reset a $200 plan | D | Studio photograph of a single crumpled receipt held between two fingers against a flat saturated red backdrop, hard direct flash, sharp shadow behind, nothing else in frame, upper two thirds, no text |
| `20260819_05` | Google's free AI stack vs paid ChatGPT | D | Studio photograph of two identical cardboard boxes on a seamless backdrop, one plain and one wrapped in gold foil, hard directional light, heavy shadow, single saturated blue background, centred in upper two thirds, no text |
| `20260819_14` | Frontier-level AI running on a laptop, offline | C | Photograph of an open laptop on a wooden kitchen table with the wifi router unplugged and visible in the background, morning window light, cool neutral tones, cable coiled beside it, upper two thirds, no text |
| `20260820_05` | Free AI agent tools compared | C | Photograph of a desk from directly above with a laptop, a notebook covered in handwritten arrows and boxes, a cold coffee, and a phone face-down, single overhead light, muted palette with one red object, no text |
| `20260820_14` | Your translated text now counts as AI-written | A | Portrait photograph of a writer at night, face half in shadow, staring past the camera, laptop glow underlighting the jaw, cold blue as the only colour, tight crop chest-up, 35mm, no text |
| `20260821_05` | 11 free tools replacing paid subscriptions | D | Photograph of a stack of unopened subscription invoices on a desk with one torn in half on top, hard low-angle light casting long shadows, saturated yellow backdrop, upper two thirds, no text |
| `20260821_14` | The AI wedding-video surprise | B | Documentary photograph of an older couple sitting on a sofa watching something off-frame, both faces lit by a warm screen glow, one hand covering the mouth in surprise, living-room clutter visible, natural imperfect framing, no text |
| `20260822_05` | What actually happened in AI this week | D | Photograph of a newspaper front page pinned to a corkboard, headlines deliberately blurred illegible, a single red pin catching hard light, desaturated except the pin, shot straight on, upper two thirds, no text |
| `20260822_14` | AI skills clients are paying for now | A | Portrait photograph of a freelancer in a small home office, arms folded, looking directly at the lens, unglamorous room with a whiteboard behind, hard side light from a window, chest-up, no text |
| `20260823_05` | Free AI courses worth finishing | C | Photograph of a laptop on a bed at night showing a paused video player, headphones tangled beside it, blanket creases lit by the screen, no other light, slight overhead angle, authentic snapshot, no text |
| `20260823_14` | Why an AI watermark remover hit 11k stars | B | Close-up photograph of a printed photo on a desk with one corner physically torn away, tweezers resting beside it, hard raking light across the paper texture, desaturated except a single green object, no text |

---

## Trending signal behind these picks

Cross-referenced 16 Aug 2026 from three live sources.

**X / Twitter** (pulled via the burner + twitter-cli, 60 posts from 5 AI accounts):
Grok 4.6 landed ~48h ago and is the dominant story — @minchoi ran it twice
(4.2k and 2.7k engagement) on games, 3D worlds and 3D prints. Running
frontier-class models **locally on a MacBook** pulled 3.5k. Pricing anger is
live: OpenAI charging **$80 to reset the usage cap on the $200 plan** (984).
Detection discourse too — Claude translations now counting as AI-generated
(4.0k). And an AI **watermark remover hit ~11k GitHub stars** (1.2k).

**Instagram** — 64 competitor posts from the last 10 days: @evolving.ai owns
the board with AI-oddity news (SF billboard 120k, useless pigeon app 93k,
em-dash discourse 52k). "Comment *Stanford*" free-lecture bait pulled 22k.
@vaibhavsisinty took two top slots with Seedance 2.5 AI video.

**YouTube** — "11 FREE AI Tools That WILL Replace Your Paid Apps" 189k,
"Google's SECRET 7 AI Tools" 476k, "I Tried 100+ AI Tools" 166k.

**The overlap** is the signal: *free and local beating paid* appears on all
three platforms at once. That is the spine of this week — six of the fourteen
slots sit on it.

⚠️ **Verify before publishing.** Slots pegged to news (`20260817_14` Grok 4.6,
`20260818_14` OpenAI pricing, `20260819_14` local models, `20260820_14`
translation policy, `20260823_14` watermark remover) come from tweet text, not
primary sources. Confirm each specific before it ships — a wrong number on a
news card is worse than a dull post.

## Caption mechanics to carry over

From the same scrape: 25% of competitor posts open with comment bait
("Comment WORD and I'll send it"), 46% ask for a follow, median caption is 771
characters. Comment-to-like ratio for the bait accounts runs 0.68–1.11 against
our 0.00. At minimum, put one comment trigger in every caption this week.
