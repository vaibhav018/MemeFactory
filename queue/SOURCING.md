# Where the clips actually come from

Traced 28 Aug 2026, because a 21-day sweep of thirteen Instagram aggregator
handles produced **four usable clips** and two of the pool's top three were
unpublishable. The aggregators are not the source. They are a slow, lossy layer
on top of one.

## The finding that matters

The Red Alert 2 film — our best-performing reel, 3,560 views — did not originate
with @evolving.ai. It was posted to **r/aivideo on 21 August**, and @evolving.ai
reposted it the same day. We posted it on **26 August**.

Five days behind a reposter who was zero days behind the source. At the source
we are same-day, and we credit the person who made the thing.

*(The Reddit poster is reported as u/Numerous-Glove-1741, title 《二十二分钟》.
Confirm that directly before crediting anyone by name — it comes from search
summaries, not from the post.)*

## Three classes, three upstreams

| Class | Examples | Real source | Reachable how |
|---|---|---|---|
| **AI films** | Red Alert 2, Westeros 2048, Norse dragon, Star Wars ballad | **r/aivideo**, then individual creators | Apify `trudax/reddit-scraper-lite` — verified working |
| **Robot / news** | Humanoid Games, launches, demos | **Official broadcast** — YouTube livestreams, CGTN, Bloomberg | Apify `streamers/youtube-scraper`, or yt-dlp |
| **Tools / repos** | licences, star counts, local models | our own screen | `scripts/record_screen.py` — already built |

AI films are the class that performs, and r/aivideo is where they surface first.

### Why the news class is the easy one

The Humanoid Games footage is not a creator's work that an aggregator lifted —
it is press footage. The event ran 22-26 August at Beijing's National Speed
Skating Oval with official livestreams on YouTube and CGTN, plus Bloomberg
coverage. Sourcing there removes the attribution problem entirely: a named
outlet instead of "original creator unnamed in the source".

### The layer below

Much of this originates on **Douyin and Bilibili** before it reaches Reddit or
X at all. That is the true headwater and Apify has actors for it, but it is
harder: Chinese-language discovery, and no crediting norms to work with. Worth
knowing, not worth building first.

## What changes if we go upstream

* **Timing.** Same-day instead of five days late.
* **Supply.** One week of r/aivideo's top posts returned more candidates than
  twenty-one days across thirteen Instagram handles.
* **Attribution.** Credit the creator instead of a reposter — which is also the
  thing `publish_reel.py` has been refusing to fudge.
* **Ranking before the crowd.** Reddit scores are visible (3,754 / 2,412 / 599
  in the sample), so a clip can be judged on community signal before any
  aggregator has touched it.

## Notes for whoever builds the sweep

* Reddit's public JSON is **403 to unauthenticated clients** now. Either an
  OAuth script app (free) or the Apify actor. The Apify route is verified and
  uses the token already in `.env`.
* **Do not use Apify's `run-sync-get-dataset-items` for the Reddit actor.** It
  hung past nine minutes twice and burned two runs. Start the run async, poll
  `/v2/actor-runs/<id>`, then read the dataset. The dataset is readable while
  the run is still going, which is how the verification above was done.
* Reddit video is DASH — audio and video are separate streams. Expect the
  download path to need more than `requests.get(url)`.
