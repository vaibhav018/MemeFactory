# MemeFactory — Handoff Notes

**Snapshot date:** 2026-08-16
**Handle:** `@profit_prompts_` (178 followers, 25 posts, MEDIA_CREATOR account)
**Next scheduled slot:** Sun 2026-08-16 14:00 UTC (19:30 IST) — currently *empty*, pipeline will fall back to auto-generation

> First prompt for laptop-Claude: **"Read HANDOFF.md and CLAUDE.md, then tell me where we left off."**

---

## What this project is

Automated Instagram carousel publisher. Runs on GitHub Actions cron (`0 5,14 * * *` UTC = 11:00 & 19:30 IST). Two content sources:

1. **Curated queue** (`queue/curated/<YYYYMMDD_HH>.json`) — hand-picked or swipe-generated posts consumed in filename order.
2. **Auto-generated fallback** — when curated queue is empty, `pipeline.py` calls the trend-based ideation engine.

Slide 1 cover: pipeline auto-uses `assets/curated/<post_id>/cover.jpg` if present; otherwise Cloudflare FLUX. Slides 2-7: always CF FLUX.

---

## Current state (Aug 16)

### Queue

- `queue/curated/` is **empty**. All 12 Gemini-covered posts (Aug 4-10) + both swipe test posts (Aug 13 eve, Aug 14 morn) have been consumed.
- Last 4 posts (Aug 14 eve → Aug 16 morn) were auto-generated fallbacks — reach dropped to 10-17 (worst of the batch).

### Reach analysis (last 20 posts, IG Graph API)

| Metric | Best | Worst | Signal |
|---|---|---|---|
| Reach | 94 (Aug 3 "5 free AI tools") | 10 (Aug 15 eve fallback) | Declining trend |
| Likes | 5 (Amazon FBA) | 0 | Very low |
| **Saves** | **2 (twice)** | **0 (17/20 posts)** | **This is the actual problem** |
| Shares | 0 across all 20 | | Zero viral loop |
| Comments | 0 across all 20 | | Zero comment bait |
| Non-follower reach | 40.5% (30d) | | IG *is* pushing to Explore |

**Diagnosis:** distribution isn't broken (IG reaches non-followers 40% of the time). Content isn't earning saves/shares → IG de-prioritizes → reach collapses.

**Swipe pipeline verified working:**
- Aug 13 eve `20260813_14` — "Realistic AI tool expertise expectations" — reach 16
- Aug 14 morn `20260814_05` — "Hacking AI resume screeners" — reach 23
- Both fired cleanly (no crashes). But underperformed curated Gemini avg (~40 reach) by 2x.

Follower context: user did follow-back growth. Followers aren't organic — reach depends on Explore, not follower graph.

---

## Open decision: Phase 3 scale vs. save-rate experiment

**Original plan** (from Aug 7): fill 14 slots for Mon Aug 17 → Sun Aug 23 with swipe-generated content.

**My revised recommendation** (based on Aug 16 reach data): **don't scale. Run a 1-week structured experiment on save-hunting formats.**

### Proposed experiment (Aug 17 → Aug 23, 2 posts/day)

| Format | Slots | Rationale |
|---|---|---|
| **A: Listicle** ("5 X that Y") | Mon/Wed/Fri morning | Aug 3 hit (94 reach) proves this format saves |
| **B: Prompt screenshot** (bold monospaced prompt fills slide) | Mon/Wed/Fri evening | Model: @askgpts — millions of saves on this format |
| **C: Deep-dive** (current curated format) | Weekends | Control group |

Plus 3 pipeline changes to build:
1. **Bold text-first covers** (72pt yellow-on-black headline, replace magazine illustrations)
2. **Explicit save CTAs** in slide 7 ("Save this before your next resume upload")
3. **Yes/no comment bait** in every caption ("ChatGPT Plus or Pro?")

**Effort:** 3-4h of pipeline work (2 writer variants + bold-text cover generator + CTA update).

**User has not confirmed** the experiment plan yet. Awaiting decision.

---

## What was built recently (Aug 6 → Aug 16)

### Aug 6 — user-cover convention
- Commit `e78e264`: pipeline auto-detects `assets/curated/<id>/cover.{jpg,jpeg,png}` for slide 1 background.
- 12 Gemini-generated covers placed under `assets/curated/2026080{4-9}_{05,14}/` (all now consumed).

### Aug 7 — swipe pipeline (copy-cat content system)
- `scripts/swipe.py` — Apify Instagram scraper (fallback: Instaloader with burner IG login). Ranks handles' top posts by (likes + comments) in last N days. Downloads cover image to `swipe/<handle>/<shortcode>.jpg`.
- `scripts/swipe_to_queue.py` — LLM-adapts scraped competitor posts into our voice via `engine/scripting/carousel_writer.write_carousel()`. Trigram dedupe vs existing queue + posted history. Drops drafts in `queue/curated_draft/` for manual review (gitignored). Copies swiped cover to `assets/curated_draft/<draft_id>/cover.jpg`.
- `scripts/promote_draft.py` — one-command approval: `python scripts/promote_draft.py <draft_id> <YYYYMMDD_HH> [--commit]`. Renames JSON to slot, moves cover, git-adds.
- `config/handles_watchlist.yaml` — 13 handles: wealthpill_, vanik.businessinstitute, aimasteryhub_, evolving.ai, coderss_world, aifired.studio, alamin.8020ai, vaibhavsisinty, evolvingscience.ai, innovation (unverified), stics.ai, thewizeai, askgpts.

### Aug 16 — Agent-Reach installed
- Location: `~/.agent-reach-venv/` (Python 3.13 venv). Activate: `source ~/.agent-reach-venv/bin/activate`.
- 5/15 channels active: YouTube (yt-dlp), RSS/Atom, V2EX, Web (Jina Reader), Bilibili search.
- Not yet installed: Twitter, Reddit, Facebook, Instagram-via-OpenCLI, XiaoHongShu, LinkedIn (all need cookie/session auth from a burner account).
- Not yet wired into `swipe.py` (Apify is still the sole scraper backend for IG).

---

## Env setup on new machine

**Required env vars in `.env` (never committed):**

```bash
# Instagram Graph API (posting + insights)
IG_ACCESS_TOKEN=<from developers.facebook.com/tools/explorer>
IG_USER_ID=28084089337890165

# LLM (writer + swipe adapter)
GROQ_API_KEY=<from console.groq.com — free tier>

# Apify (swipe scraper) — copy actual token from the previous machine's .env
APIFY_TOKEN=<paste_from_old_env>

# Optional — Instaloader fallback for swipe scraping
# IG_SWIPE_USER=<burner_ig_handle_here>
```

**Install:**

```bash
git clone https://github.com/vaibhav018/MemeFactory && cd MemeFactory
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# copy .env values from previous machine into .env

# Optional — Agent-Reach for YouTube/Reddit/etc scraping (read-only)
python3 -m venv ~/.agent-reach-venv
source ~/.agent-reach-venv/bin/activate
pip install https://github.com/Panniantong/agent-reach/archive/main.zip
mkdir -p ~/.config/yt-dlp && echo '--js-runtimes node' >> ~/.config/yt-dlp/config
npm install -g mcporter
mcporter config add exa https://mcp.exa.ai/mcp --scope home
agent-reach install --env=auto  # read-only check
```

---

## Common commands (cheat sheet)

```bash
# --- Reach analysis (paste last 20 posts + insights) ---
export $(grep -E "^IG_" .env | xargs) && python -c "
import os, requests
r = requests.get(f'https://graph.instagram.com/v21.0/{os.environ[\"IG_USER_ID\"]}/media',
    params={'fields':'id,caption,timestamp','limit':20,'access_token':os.environ['IG_ACCESS_TOKEN']}).json()
for m in r['data']:
    ir = requests.get(f'https://graph.instagram.com/v21.0/{m[\"id\"]}/insights',
        params={'metric':'reach,likes,saved,shares,comments','access_token':os.environ['IG_ACCESS_TOKEN']}).json()
    v = {d['name']: d['values'][0]['value'] for d in ir.get('data', [])}
    print(f\"{m['timestamp'][:16]}  reach={v.get('reach','-')}  saves={v.get('saved','-')}  {(m.get('caption') or '')[:60]}\")
"

# --- Weekly swipe ritual (Sunday, ~20min) ---
python scripts/swipe.py --top 12 --days 30           # scrape all 13 handles (~$0.30 Apify)
python scripts/swipe_to_queue.py --n 14 --dry-run    # preview rank+dedupe
python scripts/swipe_to_queue.py --n 14              # actually generate drafts w/ LLM
python scripts/promote_draft.py --list               # see all pending drafts + engagement
python scripts/promote_draft.py <id> 20260817_05 --commit  # promote to a slot
git push                                             # cron picks up

# --- Manual pipeline test (bypass cron) ---
gh workflow run profit-prompts --ref main            # trigger workflow_dispatch
gh run watch <run_id>                                # follow it

# --- Rescrape single handle ---
python scripts/swipe.py --handle wealthpill_ --top 5

# --- Agent-Reach: fetch YouTube video ---
source ~/.agent-reach-venv/bin/activate
yt-dlp --skip-download --get-title --get-description "<url>"
```

---

## Known issues / gotchas

1. **GitHub Actions runner sometimes 500s on `workflow_dispatch`.** Scheduled cron works fine; manual triggers occasionally fail with "job not acquired by hosted runner". Retry or wait for the next scheduled slot.
2. **Groq occasionally 429s during batch LLM calls.** `engine/llm_client.py` has exponential backoff; usually recovers within 15s.
3. **Instagram anonymous scraping is dead** in 2026 — Instaloader without login gets 429 on the first request. That's why we use Apify as the primary backend.
4. **`@aimasteryhub_` returns only 1 post from Apify** — either the account is sparse or Apify hits a default limit. Not blocking.
5. **`@innovation` handle unverified** — added to watchlist but marked as flag; scraper skips gracefully if profile doesn't exist.
6. **Local `git log` can lag behind `origin/main`** because scheduled Actions commit to remote. Always `git fetch origin main && git log HEAD..origin/main` before analyzing recent posts.
7. **`.env`, `swipe/`, `queue/curated_draft/`, `assets/curated_draft/`** are gitignored. Never staged.
8. **Apify token was pasted in chat once (Aug 7)** — treat as compromised but user cannot rotate (their words: "ill get only one time"). We use it as-is.

---

## Recent commits (git log)

```
4f99510 feat(swipe): image copy + one-command draft promotion
10921c0 chore(gitignore): exclude swipe/ + queue/curated_draft/
4a7ee04 feat(swipe): Apify backend + auto-detect
9e4925c feat(swipe): competitor-post scraper + LLM-adapt pipeline
7369aa5 feat(covers): add 12 user-generated cover images for 2026-08-04 → 08-09
e78e264 fix(pipeline): stop republishing curated posts + add cover-image convention
```

Plus ~10 auto-generated `carousel: ...` commits from the GH Actions runner.

---

## What to do next (order of priority)

1. **User decides:** run the save-rate experiment (recommended) or scale to 14/wk with existing formula.
2. If experiment: build 2 new writer variants (`carousel_writer_list.py`, `carousel_writer_prompt.py`) + bold-text cover generator + update CTAs.
3. If scale: rescrape + `swipe_to_queue.py --n 14` + promote to Mon-Sun slots.
4. Either way — **queue is empty; something needs to land before Sun 08-16 14:00 UTC** or another auto-fallback fires.

---

## Monetization roadmap (from Aug 7 discussion — not yet started)

Ranked for a solo operator with the current IG page:

1. **YouTube Shorts expansion** — repurpose carousels as 30-sec Shorts. Agent-Reach's YouTube channel now unlocks trending-Shorts scraping for the swipe pipeline. Est ₹5-20k/mo in 3mo (AdSense + affiliates).
2. **Affiliate injector** (`scripts/inject_affiliates.py`) — auto-add ref links to captions for tools mentioned. ~2h build. Instant $.
3. **Weekly newsletter** — aggregate top 30 swipe items into beehiiv digest. Free tier → paid at ~500 subs.
4. **Digital product: AI Prompt Vault** — 200 curated prompts, Gumroad @ ₹499. One-time build, passive.
5. **Sponsored posts** — needs 10k+ engaged followers first.
6. **DFY content service** — package this pipeline for other creators. ₹15-30k/mo/client.

None of these have been built. Save-rate experiment (this week) should complete before opening #1 or #2 — need to know the content formula works organically before scaling channels.
