# Cover-image prompts — for user-generated Gemini covers

The pipeline auto-uses `assets/curated/<post_id>/cover.jpg` (or `.jpeg`/`.png`)
as slide 1's background if the file exists. Slides 2-7 still get generated
by Cloudflare FLUX using the post's `image_prompts`.

**Workflow**:
1. Generate the cover in Gemini Pro (or any tool) using the prompt below.
2. Save it as `assets/curated/<post_id>/cover.jpg` (or copy it into Pictures
   and ask Claude to move it).
3. `git add` + `git push` — the next scheduled cron slot uses your image.

If a cover doesn't exist for a post, the pipeline falls back to the first
CF-generated image. Nothing breaks.

---

| Post ID (slot) | Pillar | Cover-image prompt |
|---|---|---|
| `20260803_14` (Wealth) | 3 Fiverr gigs paying $100/hr with AI | editorial illustration of Fiverr freelancers earning with AI tools, dark navy background, money-green accents, subtle gold highlights, no text, magazine style |
| `20260804_05` (Wealth) | Amazon FBA — honest math | editorial illustration of Amazon FBA warehouse boxes and profit charts, dark navy background, money-green accents, subtle gold highlights, no text, magazine style |
| `20260804_14` (AI) | Claude prompt beat $200 ChatGPT Pro | minimalist editorial illustration of Claude AI prompt engineering vs paid tools, dark navy background, cyan and green accents, glowing circuit patterns, no text, professional |
| `20260805_05` (AI) | Perplexity 15-min research trick | minimalist editorial illustration of Perplexity AI research workflow and focus mode, dark navy background, cyan and green accents, glowing circuit patterns, no text, professional |
| `20260805_14` (Wealth) | 5 side hustles for a college student | editorial illustration of a college student side hustle setup with laptop, dark navy background, money-green accents, subtle gold highlights, no text, magazine style |
| `20260806_05` (Wealth) | POD niches nobody sells in | editorial illustration of print-on-demand shirts and mugs in a niche marketplace, dark navy background, money-green accents, subtle gold highlights, no text, magazine style |
| `20260806_14` (AI) | Personal AI assistant in 30 min free | minimalist editorial illustration of a personal AI assistant workflow with Claude Projects, dark navy background, cyan and green accents, glowing circuit patterns, no text, professional |
| `20260807_05` (Tech) | iPhone battery settings Apple hides | minimalist editorial illustration of an iPhone with glowing settings toggles floating around it, dark navy background, electric cyan accents, no text, professional design |
| `20260807_14` (Wealth) | $10K/month freelance stack | editorial illustration of freelance business stack laptop desk workflow, dark navy background, money-green accents, subtle gold highlights, no text, magazine style |
| `20260808_05` (Wealth) | 3 dropshipping myths | editorial illustration of a dropshipping Shopify store analytics dashboard, dark navy background, money-green accents, subtle gold highlights, no text, magazine style |
| `20260808_14` (Tech) | 3 companies every AI tool depends on | editorial illustration of a semiconductor chip glowing with circuit patterns radiating outward to smaller devices, dark navy background, electric cyan accents, no text, magazine style |
| `20260809_05` (AI) | 5 GitHub repos replace paid SaaS | minimalist editorial illustration of GitHub open-source AI repos in a terminal dark theme, dark navy background, cyan and green accents, glowing circuit patterns, no text, professional |
| `20260809_14` (Wealth) | Boring business playbook | editorial illustration of boring businesses — laundromat, vending, storage warehouse — dark navy background, money-green accents, subtle gold highlights, no text, magazine style |
| `20260810_05` (Tech) | AI model launches worth switching to | editorial illustration of three glowing AI model icons floating in space with connection lines, dark navy background, electric cyan accents, no text, magazine style |

---

## Palette hints (in case you're not using Gemini's default rendering)

- **AI / Tech (yellow accent, blue accent)**: dark navy background `#0A0A0F`, cyan `#00D4FF`, green `#00E676`
- **Wealth (green accent)**: dark navy `#0B0F0A`, money green `#00E676`, gold `#F5C518`
- **Tech & Science (electric cyan)**: navy `#001528`, cyan blue `#20A0FF`

## Notes

- Aspect ratio: **square (1:1) or 4:5** — the pipeline resizes to 1080×1350 with center crop.
- Keep the visual centered — the pipeline overlays a semi-transparent dark
  panel behind the hook text (top-middle zone).
- No text/watermarks in the generated image — text is added by the compositor.
