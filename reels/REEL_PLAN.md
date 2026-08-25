# Reel plan — Wed 27 Aug → Tue 2 Sep 2026

Night slot, 18:30 IST, curated format. One clip, one line of commentary,
credit on screen and in the caption.

**Note:** Reels in this format have **no cover or last-slide image**. They are
a header card over a source clip — there is nothing to generate. The 14
cover/last-slide prompts you asked for are the *carousel* week, and they are in
`queue/curated/COVER_PROMPTS.md`.

---

## The daily loop

```bash
python scripts/discover_reels.py --days 14 --top 8
```

Writes preview frames to `discover/`. Look at eight images, pick one, write a
line. Everything else — crop detection, aspect, source download — is already
solved by the sweep.

Then tell Claude the shortcode and your line, or build the job yourself from
`reels/data/posted/20260826_13.curated.json` as the template.

---

## What actually earns the slot

From the first sweep, ranked by engagement across the watchlist. The pattern is
unambiguous:

| Engagement | Length | Subject |
|---|---|---|
| 22,385 | 12.4s | Robot beats Bolt's 100m record |
| 19,975 | 33.0s | Robot's absurd 400m running form |
| 19,405 | 20.9s | Robot scores a free kick, does the SIUUU |

**Short wins.** The 12.4s clip beat the 33s one. Completion rate is the metric
Reels rewards, and a 12-second clip is far more likely to be watched twice.

**Physical, visible, absurd.** Every top clip is a machine doing something a
human does, slightly wrong. Nothing abstract, nothing that needs explaining.

**Under 30 seconds.** Anything past that had lower engagement in the sample,
even from the same account.

---

## Seven days of themes

Themes, not fixed topics — the sweep tells you what actually exists that day.
Ranked roughly by how reliably clips turn up.

| Day | Theme | What to look for |
|---|---|---|
| **Wed 27** | Robots failing | The Games are still running. Falls, stumbles, collisions. Failure outperforms success — it is funnier and it is honest |
| **Thu 28** | AI video that fooled people | A clip people argued was real. The argument *is* the hook |
| **Fri 29** | Something built in a weekend | One person, a free tool, a result that looks expensive |
| **Sat 30** | Before / after | Same prompt, last year's model against this month's. The gap does the work |
| **Sun 31** | The uncanny one | Almost right, wrong in a way you cannot unsee. High save rate, high comment rate |
| **Mon 1** | A tool doing a real job | Not a demo. Someone's actual work, actually shipped |
| **Tue 2** | Weekly roundup clip | The single best thing of the week, whatever it was |

---

## Rules for the commentary line

- One or two lines. `**bold**` the phrase that carries it — usually a number.
- State the fact, not a reaction. "A robot ran 100m in **9.39 seconds**" beats
  "This is INSANE 🤯".
- **Verify before writing.** The first candidate's own caption said
  "X-Humanoid's TienKung Ultra" and claimed a record with no time. The real
  facts: Tiangong Ultra, Beijing Humanoid Robot Innovation Centre, 9.39s. Names
  and numbers in a reposted caption are frequently wrong.
- No comment bait. Reach fell 44% the week every caption carried it.

## Credit

`credit.name` is a hard stop — the publisher refuses to render without it.
Prefer the **original** source over whoever reposted it. Tonight's clip is
credited to the World Humanoid Robot Games broadcast, not to the account it was
found on.

Tag them in the caption too. On-screen credit reaches viewers; a caption tag
reaches the creator, who sometimes reshares.

---

## On audio

API-published Reels **cannot use Instagram's music library** — no trending
sounds, and audio cannot be added after publishing. Music must be in the file
before upload.

The source clip's own audio carries through, which is usually right for
found footage. Tonight's reel published with the CCTV broadcast feed.

If a clip has weak or no audio and you want a trending sound, run the workflow
with `dry_run: true`. It renders and pushes the MP4 without publishing; you
download it, post from the phone, and pick the audio in the app. One minute of
manual work for the biggest reach lever on Reels — worth testing on a clip
where the native audio adds nothing.

---

## First one is live

`20260826_13` — robot beats Bolt, 12.4s, published 25 Aug 18:58 UTC.
https://www.instagram.com/reel/DceVeGcEUOJ/

Check its reach in two days against the carousel average of ~21. That number
decides whether the night slot stays a Reel.
