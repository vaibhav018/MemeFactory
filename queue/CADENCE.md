# Cadence — 27 Aug to 9 Sep 2026

**11 reels, 3 carousels, one post a day.** Reels at 18:30 IST, carousels at
11:00 IST.

## Why the split changed

Numbers from the Instagram insights API, 20-27 Aug:

| Post | Views | Reach | Likes | Saves |
|---|---:|---:|---:|---:|
| Reel — Red Alert 2 (26 Aug 19:14) | **3,560** | **2,972** | 40 | **17** |
| Reel — first curated (26 Aug 00:38) | 606 | 438 | 6 | 0 |
| Carousel — roundup, 5 video slides (26 Aug 16:28) | 18 | 11 | 4 | 0 |
| Carousel — stills (26 Aug 15:32) | 19 | 13 | 3 | 0 |
| Carousel — stills (23 Aug 11:25) | 54 | 25 | 2 | 0 |
| Carousel — stills (21 Aug 19:53) | 66 | 23 | 2 | 3 |

Reels out-reach carousels by roughly **150x** on this account.

One thing the numbers rule out: the video slides are not what held the roundup
back. The all-stills carousel posted an hour earlier the same day landed 19
views to its 18, and every carousel going back a week sits in the same 11-25
reach band. Carousel reach here is structurally flat regardless of what is on
the slides — it goes to followers and stops. Reels go to people who do not
follow the account yet, which is the entire difference.

Two carousels also went out within an hour on 26 Aug, splitting what little
reach there was. One post a day from here.

Saves are the number worth watching. The reel took 17; no carousel has ever
taken more than 3. Saves feed ranking harder than likes do.

## Where 11 reels come from

Supply is the constraint, not ideas. Three routes:

| Route | Proven? | Supply | Cost |
|---|---|---|---|
| **Found footage** (`scripts/discover_reels.py`) | yes — both reels so far | rationed, see below | must credit |
| **Self-recorded** (`scripts/record_screen.py`) | not yet as a standalone reel | unlimited | free |
| **Generated** (Seedance via Dreamina) | not yet | blocked | free tier |

The 21-day sweep across six handles previously returned 13 clips and only
@evolving.ai was productive. Eleven reels in a fortnight is more than that rate
supports, so the plan mixes routes rather than pretending found footage scales.

Self-recorded reels are the untested half. A repo page scrolling for 20 seconds
is not the same kind of object as a Red Alert 2 recreation, and it should not be
assumed to carry a reel on its own — the first one is an experiment, and if it
lands under 500 views the route is for carousel slides only.

## The fortnight

| Date | Format | Topic | Clip / route |
|---|---|---|---|
| Thu 27 Aug | **carousel 1** | Chinese open models beating the paid ones | self — *posted* |
| Fri 28 Aug | reel | Star Wars as a 1940s German folk ballad | `DcYeInaAtF6` |
| Sat 29 Aug | reel | Trade war as an AI music video | `DceNWd7Abs7` |
| Sun 30 Aug | reel | Run a real model on your laptop, free | self — **the experiment** |
| Mon 31 Aug | reel | Tiangong Omni runs 400m in 45.66s | `Dca_mVYgm48` |
| Tue 1 Sep | **carousel 2** | What the humanoid games actually proved | found |
| Wed 2 Sep | reel | Chinese mythology meets a Norse world-ender | `DcdnWnbgAsp` |
| Thu 3 Sep | reel | Seedance 2.5 | **blocked** — needs a generated clip |
| Fri 4 Sep | reel | Westeros survives into 2048 | `DcWNqUTAezL` — **crop by hand first** |
| Sat 5 Sep | reel | The repo that quietly hit 202K stars | self |
| Sun 6 Sep | **carousel 3** | Weekly roundup #2 | found |
| Mon 7 Sep | reel | The Odyssey as the Vietnam War | `Dbq0RjMg8IO` |
| Tue 8 Sep | reel | *unassigned* | needs a sweep around 3 Sep |
| Wed 9 Sep | reel | Free AI tools you can legally bill for | self |

Nine of eleven reel slots have a clip or a route. One is blocked on Seedance,
one needs a fresh sweep. That is the honest state, not a full fortnight.

## The pool, and what the sweep actually says

`discover/candidates.json` — 28 candidates, 21 days, 14 handles.

Twelve of the top twenty-four are @vaibhavsisinty, all face-on-camera, all
unusable here. Of the remainder, six were already spent on the 26 Aug roundup
and last night's reel. **Four genuinely new clips came out of a full sweep.**
That is the number that matters: the watchlist cannot feed eleven reels a
fortnight, and no amount of scheduling fixes that.

The clips that work share one shape: **AI-generated cinematic recreations of
something the audience already loves.** Red Alert 2 (3,560 views for us), Star
Wars, Game of Thrones, the trade war as a folk song. Robot footage is the second
vein. Neither is a "tool tip".

The lever is upstream. @evolving.ai is an aggregator; the caption on the Star
Wars clip names @demonflyingfox as the creator, and a probe of that handle
returned four reels in thirty days — lower volume, but **every one came back
"already raw"**: no aggregator header to crop around, and credit goes to the
person who made it. Its top post scored 56,181, higher than anything
@evolving.ai posted in the window bar one.

Following original creators rather than aggregators is the supply fix. It needs
more such handles found and added to `config/handles_watchlist.yaml`.

One incidental find worth keeping: `Dbv0Eo3g3Li` is @demonflyingfox running
"33 days of unlimited Seedance 2.5" on @higgsfield.ai. Higgsfield is a second
route to a Seedance clip if Dreamina is awkward.

Two handling notes on this batch:

* The music videos run 165-180s. They need a 20-second excerpt chosen by hand,
  not a `startFrom` guessed from the middle.
* `DcWNqUTAezL` came back with a 5.6%-tall crop, which is @evolving.ai's header,
  not the film. Dark letterboxed footage can lose the longest-lit-run contest to
  a bright unbroken banner. detect_band now marks a band under 25% of frame
  height `suspect`, prints it loudly, and publish_reel refuses to publish one.

## How a day gets scheduled

Nothing is date-driven in the workflows any more. The queue is the schedule:

* **Carousel** — `.github/workflows/profit_prompts.yml` looks for
  `Generated_Memes/<YYYYMMDD>_*/carousel.json` matching today in IST. Found:
  publish it. Not found: reel-only day, exit clean. There is no live-generation
  fallback; a day with nothing built gets nothing.
* **Reel** — `.github/workflows/profit_prompts_reel.yml` publishes the oldest
  non-fixture job in `reels/data/`. Empty queue is a clean exit.

Both run their slot plus two hourly catch-ups, and each attempt asks Instagram
whether the slot is already filled before doing any work. This exists because
the 27 Aug 11:00 slot was never triggered at all — active workflow, correct
cron, no run in the history.

## Verified numbers (26 Aug 2026, GitHub API)

Re-check before each post — these move daily.

| Repo | Stars | Licence |
|---|---|---|
| n8n-io/n8n | 202,475 | Sustainable Use (NOT open source — say so) |
| significant-gravitas/AutoGPT | 186,878 | MIT |
| ollama/ollama | 179,473 | MIT |
| f/awesome-chatgpt-prompts | 167,926 | CC0 |
| AUTOMATIC1111/stable-diffusion-webui | 164,669 | AGPL-3.0 |
| huggingface/transformers | 164,455 | Apache-2.0 |
| open-webui/open-webui | 149,964 | BSD-3 |
| langchain-ai/langchain | 145,033 | MIT |
| comfyanonymous/ComfyUI | 130,056 | GPL-3.0 |
| ggml-org/llama.cpp | 125,713 | MIT |
| deepseek-ai/DeepSeek-V3 | 104,417 | MIT |
| vllm-project/vllm | 90,100 | Apache-2.0 |
| QwenLM/Qwen3 | 27,557 | Apache-2.0 |
| MoonshotAI/Kimi-K2 | 11,104 | Modified MIT |
| zai-org/GLM-4.5 | 4,415 | Apache-2.0 |
