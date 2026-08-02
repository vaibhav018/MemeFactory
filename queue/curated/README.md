# queue/curated/

**Hand-authored posts waiting to publish.** The pipeline picks the oldest
file here on every scheduled slot (11:00 AM IST + 7:30 PM IST daily) —
skips all LLM ideation/writing and just does image gen + composite + IG.

Every Sunday, we (Claude in a live session) curate the coming week's
14 posts and drop them here. This trades real-time automation for
Claude-authored insider-voice quality.

## File shape

Each file: `YYYYMMDD_HH.json` where HH is `05` (morning slot) or `14`
(evening slot). Files are consumed alphabetically, so filenames double as
schedule.

Required fields:
```json
{
  "id": "20260803_05",
  "pillar_id": "ai_tools_workflows",
  "pillar_name": "AI Tools & Workflows",
  "topic": "5 free AI tools quietly replacing paid SaaS",
  "angle": "one-sentence contrarian entry point",
  "hook": "slide-1 text — 8-14 words, curiosity pattern A/B/C/D",
  "caption": "IG caption in insider voice + question + hashtags",
  "slides": [ {"slide": 1, ...}, ..., {"slide": 7, ...} ],
  "image_prompts": [ "prompt A", "prompt B", "prompt C" ]
}
```

Optional: `image_paths: ["assets/curated/20260803_05/img_1.jpg", ...]`
If present, pipeline uses these files instead of calling Cloudflare FLUX.
Drop Gemini-Pro-generated images here to get exactly the visual you want.

## Consumed on publish

Successful publish deletes the source .json — the equivalent of moving
it to `posted/` (which the pipeline also does for the runtime-generated
`queue/pending/<runid>.json`).

## Failure mode

If the queue is empty on a scheduled slot, GH Actions falls back to
live `python pipeline.py --publish` so the account still posts. This
means the account never goes silent even if a Sunday curation is missed.
