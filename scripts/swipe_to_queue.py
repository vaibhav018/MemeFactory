"""
Swipe → queue pipeline. Reads swipe/<handle>/latest.json files, ranks the
top-engaging competitor posts, dedupes vs already-queued and recently-posted
topics, then uses the existing LLM writer to rewrite each into a full
7-slide carousel in OUR brand voice — never copying phrases.

Output lands in queue/curated_draft/ for human review. Move approved files
to queue/curated/ (any post_id name works) and the pipeline auto-picks them.

Usage:
  python scripts/swipe_to_queue.py                # process default N=8
  python scripts/swipe_to_queue.py --n 4          # fewer new drafts
  python scripts/swipe_to_queue.py --pillar ai_tools_workflows  # one pillar
  python scripts/swipe_to_queue.py --dry-run      # rank + dedupe, no LLM

Provenance: each draft embeds source_handle + source_shortcode + source_url
so you can always trace back and cross-check the swiped post.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import yaml

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=BASE / ".env")
except ImportError:
    pass

from engine import llm_client  # noqa: E402
from engine.scripting.carousel_writer import write_carousel  # noqa: E402


PILLARS_DIR = BASE / "config" / "pillars"
CURATED_DIR = BASE / "queue" / "curated"
DRAFT_DIR = BASE / "queue" / "curated_draft"
POSTED_DIR = BASE / "queue" / "posted"
DRAFT_ASSETS_DIR = BASE / "assets" / "curated_draft"
SWIPE_DIR = BASE / "swipe"

# How similar (0..1) a competitor topic must be to something we already have
# in the queue or posted history before we skip it. Uses trigram overlap.
DEDUPE_THRESHOLD = 0.35


def load_pillars() -> dict[str, dict]:
    out = {}
    for path in sorted(PILLARS_DIR.glob("*.yaml")):
        with path.open(encoding="utf-8") as f:
            pillar = yaml.safe_load(f)
        out[pillar["id"]] = pillar
    return out


def load_swipes() -> list[dict]:
    """Flatten every swipe/<handle>/latest.json into one list of posts."""
    posts = []
    if not SWIPE_DIR.exists():
        return posts
    for latest in SWIPE_DIR.glob("*/latest.json"):
        try:
            data = json.loads(latest.read_text())
        except Exception as e:
            print(f"  [warn] could not read {latest.relative_to(BASE)}: {e}")
            continue
        for post in data.get("top", []):
            post["source_handle"] = data["handle"]
            post["source_pillars"] = data.get("pillar_affinity", []) or []
            posts.append(post)
    return posts


def _trigrams(s: str) -> set[str]:
    s = re.sub(r"[^a-z0-9 ]", " ", s.lower())
    s = re.sub(r"\s+", " ", s).strip()
    tokens = [f" {t} " for t in s.split()]
    grams: set[str] = set()
    for t in tokens:
        for i in range(len(t) - 2):
            grams.add(t[i:i+3])
    return grams


def _similarity(a: str, b: str) -> float:
    ga, gb = _trigrams(a), _trigrams(b)
    if not ga or not gb:
        return 0.0
    return len(ga & gb) / len(ga | gb)


def load_known_topics() -> list[str]:
    """Everything already queued + recently posted — we dedupe against these."""
    known: list[str] = []
    for d in (CURATED_DIR, DRAFT_DIR, POSTED_DIR):
        if not d.exists():
            continue
        for f in d.glob("*.json"):
            try:
                data = json.loads(f.read_text())
            except Exception:
                continue
            for key in ("topic", "hook", "title"):
                if key in data and data[key]:
                    known.append(str(data[key]))
    return known


def is_duplicate(candidate_text: str, known: list[str]) -> tuple[bool, str]:
    for k in known:
        sim = _similarity(candidate_text, k)
        if sim >= DEDUPE_THRESHOLD:
            return True, k
    return False, ""


def pick_pillar(post: dict, pillars: dict[str, dict]) -> dict | None:
    """First pillar in the handle's pillar_affinity that we actually have configured."""
    for pid in post.get("source_pillars", []):
        if pid in pillars:
            return pillars[pid]
    return None


ADAPT_SYSTEM = """You are a content strategist for an Instagram carousel brand
targeting curious 18-35 year-olds in India and the diaspora. You are looking
at a high-performing post from a competitor account. Your job is to extract
the underlying TOPIC and ANGLE — the reason people saved and shared it —
and re-express it as a fresh post idea in OUR brand voice.

Non-negotiables:
  - Do NOT copy phrases, sentence structures, or opening lines from the
    competitor's caption. Extract the idea, throw away their words.
  - Do NOT keep any competitor-specific product mentions, personal stories,
    or "as I mentioned in yesterday's post" references.
  - Our voice: direct, insider, "here's what I do", one specific number
    over ten vague ones, no guru-hype, no emoji-spam.
  - The topic must fit the given pillar. If the competitor post is off-pillar,
    reframe it toward the pillar's audience.

Return ONLY a valid JSON object (no markdown fences) with these fields:
  {
    "topic":     "8-14 word specific topic in our voice",
    "angle":     "one sentence — the insight or contrarian take we lead with",
    "hook":      "8-14 word hook line — curiosity/stat/contrast/question pattern",
    "caption":   "2-4 sentence IG caption in our voice + a single-question CTA",
    "image_prompts": [
       "editorial cover illustration prompt — magazine style, dark navy background, pillar-appropriate accents, no text",
       "second slide background prompt — abstract or data-viz, on-brand",
       "third slide background prompt — cinematic or environmental, on-brand"
    ]
  }
"""


def adapt_topic(post: dict, pillar: dict) -> dict:
    caption = post.get("caption", "")[:1200]
    user = f"""Pillar: {pillar['name']} ({pillar['id']})
Pillar description: {pillar['description']}

Competitor account: @{post['source_handle']}
Engagement: {post['likes']} likes + {post['comments']} comments
Original caption:
\"\"\"
{caption}
\"\"\"

Adapt this into a topic idea for OUR pillar. Follow the non-negotiables strictly."""
    result = llm_client.complete_json(ADAPT_SYSTEM, user)
    if isinstance(result, list):
        result = result[0]
    return result


def build_curated_post(topic_data: dict, slides: list[dict], pillar: dict, post: dict) -> dict:
    # Deterministic ID for the draft file — user renames on approval.
    short_hash = hashlib.sha1(
        f"{post['source_handle']}:{post['shortcode']}".encode()
    ).hexdigest()[:6]
    draft_id = f"swipe_{post['source_handle']}_{short_hash}"
    return {
        "id": draft_id,
        "pillar_id": pillar["id"],
        "pillar_name": pillar["name"],
        "topic": topic_data["topic"],
        "angle": topic_data["angle"],
        "hook": topic_data["hook"],
        "caption": topic_data["caption"],
        "slides": slides,
        "image_prompts": topic_data.get("image_prompts", []),
        "authored_by": "swipe_adapter",
        "source": {
            "handle": post["source_handle"],
            "shortcode": post["shortcode"],
            "url": post["url"],
            "likes": post["likes"],
            "comments": post["comments"],
            "scraped_from_caption_snippet": (post.get("caption") or "")[:200],
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=8, help="Max drafts to produce (default 8)")
    ap.add_argument("--pillar", help="Restrict to one pillar id")
    ap.add_argument("--dry-run", action="store_true", help="Rank + dedupe, skip LLM")
    args = ap.parse_args()

    pillars = load_pillars()
    posts = load_swipes()
    if not posts:
        print("No swipe/*/latest.json found. Run scripts/swipe.py first.")
        return 1

    # Rank across all handles by absolute engagement. Cheap and works because
    # the handles are roughly the same size — for very asymmetric follower
    # counts, switch to engagement_rate = engagement / follower_count later.
    posts.sort(key=lambda p: p.get("engagement", 0), reverse=True)

    known = load_known_topics()
    DRAFT_DIR.mkdir(parents=True, exist_ok=True)

    drafts_made = 0
    seen_this_run: list[str] = []

    print(f"Ranked {len(posts)} candidate posts. Producing up to {args.n} drafts.\n")
    for post in posts:
        if drafts_made >= args.n:
            break

        pillar = pick_pillar(post, pillars)
        if pillar is None:
            print(f"  [skip] @{post['source_handle']}/{post['shortcode']} — no matching pillar")
            continue
        if args.pillar and pillar["id"] != args.pillar:
            continue

        preview = (post.get("caption") or "").splitlines()[0][:80]
        dup, match = is_duplicate(preview, known + seen_this_run)
        if dup:
            print(f"  [skip] @{post['source_handle']}/{post['shortcode']} — dup of \"{match[:60]}\"")
            continue

        if args.dry_run:
            print(f"  [dry]  @{post['source_handle']}/{post['shortcode']} → {pillar['id']}: {preview}")
            drafts_made += 1
            seen_this_run.append(preview)
            continue

        print(f"→ adapting @{post['source_handle']}/{post['shortcode']} → {pillar['id']}")
        try:
            topic_data = adapt_topic(post, pillar)
        except Exception as e:
            print(f"   [err] adapt failed: {type(e).__name__}: {e}")
            continue

        # Second dedupe pass, this time on the LLM-generated topic itself.
        dup, match = is_duplicate(topic_data.get("topic", ""), known + seen_this_run)
        if dup:
            print(f"   [skip after adapt] dup of \"{match[:60]}\"")
            continue

        try:
            slides = write_carousel(topic_data, pillar)
        except Exception as e:
            print(f"   [err] write_carousel failed: {type(e).__name__}: {e}")
            continue

        curated = build_curated_post(topic_data, slides, pillar, post)
        out_path = DRAFT_DIR / f"{curated['id']}.json"
        out_path.write_text(json.dumps(curated, indent=2, ensure_ascii=False))

        # Copy source cover image into the draft's assets slot so it lands as
        # slide 1 background when the draft is promoted to queue/curated/.
        src_rel = post.get("image_path")  # relative path recorded by swipe.py
        if src_rel:
            src = BASE / src_rel
            if src.exists():
                dst_dir = DRAFT_ASSETS_DIR / curated["id"]
                dst_dir.mkdir(parents=True, exist_ok=True)
                dst = dst_dir / "cover.jpg"
                dst.write_bytes(src.read_bytes())
                curated["source"]["local_cover_path"] = str(dst.relative_to(BASE))
                # Persist the updated JSON so the local_cover_path is recorded.
                out_path.write_text(json.dumps(curated, indent=2, ensure_ascii=False))
                print(f"   ✓ {out_path.relative_to(BASE)}  + cover ({dst.stat().st_size // 1024}KB)")
            else:
                print(f"   ✓ {out_path.relative_to(BASE)}  (no cover — {src_rel} missing)")
        else:
            print(f"   ✓ {out_path.relative_to(BASE)}  (no cover in swipe data)")
        drafts_made += 1
        seen_this_run.append(topic_data["topic"])

    print(f"\nDone. {drafts_made} draft(s) written to {DRAFT_DIR.relative_to(BASE)}/")
    print("Review each. To publish: rename to queue/curated/<YYYYMMDD_HH>.json + git push.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
