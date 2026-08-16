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
| `20260817_14` | AI video that directs itself (Seedance 2.5) | B | Documentary photograph of a young filmmaker in a dim editing suite, face lit only by three glowing monitors, hand frozen mid-gesture toward the screen, teal monitor glow as the single colour, grain visible, upper two thirds, no text |
| `20260818_05` | Free Stanford + Google AI certifications | A | Portrait photograph of a student in a university corridor, backpack on one shoulder, looking directly into the lens with a slight smile, hard window light from the left, warm neutral background thrown out of focus, chest-up, upper two thirds, no text |
| `20260818_14` | The useless AI app that went viral anyway | B | Photograph of a phone lying face-up on a rumpled bedsheet at night showing a nearly empty pastel app screen, room dark, only the screen lighting the fabric, slightly overhead angle, authentic snapshot quality, no text |
| `20260819_05` | Google's free AI stack vs paid ChatGPT | D | Studio photograph of two identical cardboard boxes on a seamless backdrop, one plain and one wrapped in gold foil, hard directional light, heavy shadow, single saturated blue background, centred in upper two thirds, no text |
| `20260819_14` | AI app builders that actually ship | C | Close-up photograph of two hands typing on a mechanical keyboard, a laptop screen out of focus behind showing coloured code blocks, hard rim light from the right, near-black background, upper two thirds, no text |
| `20260820_05` | Free AI agent tools compared | C | Photograph of a desk from directly above with a laptop, a notebook covered in handwritten arrows and boxes, a cold coffee, and a phone face-down, single overhead light, muted palette with one red object, no text |
| `20260820_14` | Making AI writing undetectable | A | Portrait photograph of a writer at night, face half in shadow, staring past the camera, laptop glow underlighting the jaw, cold blue as the only colour, tight crop chest-up, 35mm, no text |
| `20260821_05` | 11 free tools replacing paid subscriptions | D | Photograph of a stack of unopened subscription invoices on a desk with one torn in half on top, hard low-angle light casting long shadows, saturated yellow backdrop, upper two thirds, no text |
| `20260821_14` | The AI wedding-video surprise | B | Documentary photograph of an older couple sitting on a sofa watching something off-frame, both faces lit by a warm screen glow, one hand covering the mouth in surprise, living-room clutter visible, natural imperfect framing, no text |
| `20260822_05` | What actually happened in AI this week | D | Photograph of a newspaper front page pinned to a corkboard, headlines deliberately blurred illegible, a single red pin catching hard light, desaturated except the pin, shot straight on, upper two thirds, no text |
| `20260822_14` | AI skills clients are paying for now | A | Portrait photograph of a freelancer in a small home office, arms folded, looking directly at the lens, unglamorous room with a whiteboard behind, hard side light from a window, chest-up, no text |
| `20260823_05` | Free AI courses worth finishing | C | Photograph of a laptop on a bed at night showing a paused video player, headphones tangled beside it, blanket creases lit by the screen, no other light, slight overhead angle, authentic snapshot, no text |
| `20260823_14` | The AI story nobody reported properly | B | Photograph of an empty office corridor at night with one lit doorway at the far end, fluorescent green cast, wide angle, deep perspective, human silhouette barely visible in the doorway, upper two thirds, no text |

---

## Trending signal behind these picks

Cross-referenced 16 Aug 2026 from two sources.

**Instagram** — 64 competitor posts from the last 10 days, ranked by engagement:
@evolving.ai owns the top of the board with AI-oddity news (SF billboard fine
print 120k, useless pigeon app 93k, em-dash discourse 52k, AI Overviews comedy
22k). Free-education bait ranks high too — "comment *Stanford*" pulled 22k.
@vaibhavsisinty took two of the top slots with **Seedance 2.5** AI video.

**YouTube** — "11 FREE AI Tools That WILL Replace Your Paid Apps" 189k views,
"Google's SECRET 7 AI Tools" 476k, "I Tried 100+ AI Tools" 166k, plus a Seedance
2.5 free-tools video. Free-replacing-paid and AI video are hot on both platforms
simultaneously, which is the strongest signal available.

⚠️ **Verify before publishing.** The news-pegged slots (`20260817_14` Seedance,
`20260818_14` viral app, `20260822_05` weekly roundup) are inferred from
competitor caption snippets, not from primary sources. Confirm the specifics
before these go out — a wrong detail on a news card is worse than a dull post.

## Caption mechanics to carry over

From the same scrape: 25% of competitor posts open with comment bait
("Comment WORD and I'll send it"), 46% ask for a follow, median caption is 771
characters. Comment-to-like ratio for the bait accounts runs 0.68–1.11 against
our 0.00. At minimum, put one comment trigger in every caption this week.
