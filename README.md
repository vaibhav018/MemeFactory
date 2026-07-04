# MemeFactory - Telugu/Hindi Meme Generation Pipeline

Automated pipeline for `@mana_telugu_trolls`: pulls trending Telugu/Hindi news,
picks a meme emotion + punchline, matches a reaction image from Google Drive,
composites a 1080x1350 Instagram-ready meme, and queues 3 memes/day for
posting at 8AM / 1PM / 9PM.

## Folder structure

```
MemeFactory/
  config.json              # all constants: API keys refs, Drive folder IDs, emotion rules, times
  config_loader.py         # shared config/logging/Drive-auth helper used by every module
  news_scraper.py          # Step 1 (06:00) - fetch + rank trending stories
  emotion_matcher.py        # Step 2 (06:15) - assign emotion + punchline
  reaction_picker.py        # Step 3 (06:20) - pick + download a matching reaction image
  meme_compositor.py        # Step 4 (06:30) - overlay captions + watermark, save 1080x1350
  drive_uploader.py         # Uploads memes + logs to Drive
  scheduler.py              # Wires all steps together on a cron schedule
  requirements.txt
  .env.example              # copy to .env and fill in secrets
  data/
    emotion_reaction_index.csv   # character_emotion_number.jpg index (auto-synced or hand-edited)
    news_cache.json              # Step 1 output
    emotion_matched.json          # Step 2 output
    reaction_selection.json       # Step 3 output
    queue.json                    # today's 3 posting slots
  credentials/
    service_account.json          # Drive service account key (you provide this - gitignored)
  assets/fonts/                   # Telugu + Latin TTF fonts (you provide these - see SETUP_FONTS.txt)
  output/
    memes/                        # composited meme images
    logs/pipeline.log             # combined pipeline log
```

## 1. Install dependencies

```
python -m venv .venv
.venv\Scripts\activate            # Windows
pip install -r requirements.txt
```

## 2. newsdata.io key

1. Get a free-tier key at newsdata.io.
2. Copy `.env.example` to `.env` and set `NEWSDATA_API_KEY=...`.

newsdata.io's `/latest` endpoint returns genuine native-script Telugu/Hindi
articles (queried with `country=in&language=te,hi&category=...`), which RSS
often doesn't (many Telugu outlets title their RSS entries in English). Its
free tier delays articles ~12 hours, so on pure recency it usually loses to
same-day RSS entries - `news.min_newsdataio_stories` in `config.json`
reserves a floor (default 3 of the daily 10) so native-script content isn't
crowded out. Free tier is limited to 10 articles/request and roughly 200
requests/day - comfortably enough for one fetch/day.

## 3. Google Drive service account setup

The pipeline reads reaction images and writes memes/logs to Drive using a
**service account** (no browser login required, works unattended on a
schedule).

1. In Google Cloud Console, create or select a project.
2. Enable the **Google Drive API** for that project.
3. Create a **Service Account** (IAM & Admin -> Service Accounts), then
   generate a JSON key for it.
4. Save that JSON key file as `credentials/service_account.json`.
5. Open the JSON file and copy its `client_email` value.
6. In Google Drive, share these folders with that email as **Editor**:
   - The Reaction_images folder (ID `1zJyZk3xRxVZfxmS9t_G9MAVy0LJBkN-c`)
   - The parent MemeFactory folder (ID `1j49CKDxqvGQ1TQtrewwHqqg4KPUHkZm4`)
     - `drive_uploader.py` auto-creates `Generated_Memes/` and `Logs/`
       subfolders under this the first time it runs live.

Until `credentials/service_account.json` exists, every module automatically
falls back to offline/dry-run behavior (placeholder reaction images, no
uploads) so you can build and test without Drive access.

## 4. Fonts

Pillow needs real TTF files to render Telugu glyphs - see
`assets/fonts/SETUP_FONTS.txt` for exactly which two files to drop in
(`NotoSansTelugu-Bold.ttf`, `Roboto-Bold.ttf`). Without them, captions still
render (using Pillow's built-in font) but Telugu text will show as empty
boxes - only Hinglish/Latin punchlines will be legible.

## 5. Reaction images index

Upload your reaction images to the Reaction_images Drive folder using the
naming convention `character_emotion_number.jpg` (e.g.
`brahmanandam_laughing_02.jpg`). Then build the index:

```
python reaction_picker.py --sync-index
```

This regenerates `data/emotion_reaction_index.csv` from the live Drive
listing. Files that don't match the naming pattern are skipped (add them to
the CSV by hand if you want to use them anyway); manual rows not found in
Drive on a given sync are kept and flagged in the `notes` column rather than
deleted.

## 6. dry_run mode

`config.json`'s `app.dry_run` (default `true`) controls whether Drive uploads
actually happen. In dry-run, every step still runs normally and produces real
local output (news cache, matched emotions, composited memes) - only the
final Drive upload is skipped and logged instead. Flip it to `false` once
your service account + folder sharing are set up, or override per-command
with `--dry-run` / `--live` on `drive_uploader.py` and `scheduler.py`.

## Testing each module standalone

```
python news_scraper.py --offline       # sample data, no network calls
python news_scraper.py                 # real NewsAPI + RSS fetch

python emotion_matcher.py              # reads data/news_cache.json

python reaction_picker.py --emotion angry   # pick+download one image
python reaction_picker.py                   # process data/emotion_matched.json

python meme_compositor.py              # reads data/reaction_selection.json

python drive_uploader.py --dry-run     # log intended uploads only
python drive_uploader.py --live        # actually upload (needs service account)
```

Each step reads the previous step's JSON output file, so you can re-run any
single step repeatedly while iterating without re-running the whole chain.

## Running the full pipeline

One-off manual run (useful for testing the whole chain immediately):

```
python scheduler.py --run-now generate    # steps 1-4 + build today's queue + upload
python scheduler.py --run-now post --post-time 08:00   # publish one queued slot
```

Long-running scheduled mode (what actually runs in production):

```
python scheduler.py
```

This registers 7 cron jobs (news fetch, emotion match, reaction pick, meme
compositor+queue-build, and one post job per entry in `schedule.post_times`)
and blocks forever. Run it under a process supervisor so it survives
reboots/crashes - e.g. Windows Task Scheduler ("run at log on", restart on
failure), NSSM as a Windows service, or `pm2`/systemd on Linux.

## Known limitations

- **No direct Instagram posting.** `scheduler.py`'s post_times jobs push the
  queued meme to Drive's `Generated_Memes/` folder as publish-ready output.
  Actually publishing to Instagram requires a Meta Business API app + review
  process, which is a separate integration deliberately out of scope here.
- **newsdata.io free tier delays articles ~12h** and caps at 10/request - RSS
  covers the same-day freshness gap; `min_newsdataio_stories` guarantees
  native-script representation regardless.
- **Log rotation isn't configured** - `output/logs/pipeline.log` grows
  unbounded; add a `RotatingFileHandler` in `config_loader.get_logger` if you
  run this for a long time unattended.
