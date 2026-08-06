"""Profit Prompts — Instagram carousel content pipeline (@profit_prompts_).

Usage:
  python pipeline.py                  # full run: generate → quality → queue
  python pipeline.py --dry-run        # no API calls, no file writes to queue
  python pipeline.py --publish        # generate + auto-approve + publish (CI mode)
  python pipeline.py --retries 3      # retry if quality gates fail (default: 2)

Flow:
  1. Select pillar (weighted round-robin with recency penalty)
  2. Generate topic + angle (Claude)
  3. Write 7-slide carousel (Claude)
  4. Generate background (DALL-E 3 or gradient fallback)
  5. Compose slides (Pillow)
  6. Quality gates (7 checks)
  7. Write to queue/pending/ for human approval  (or auto-publish if --publish)
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

from engine.ideation.pillar_selector import select_pillar
from engine.ideation.topic_generator import generate_topic
from engine.scripting.carousel_writer import write_carousel
from engine.visual.background_gen import generate_background
from engine.visual.carousel_compositor import compose_carousel
from engine.quality.gates import run_gates
from engine.analytics.tracker import (
    get_db, get_recent_pillar_ids, get_recent_topics,
    record_post, update_pillar_weights,
)
from engine.publish.instagram_client import publish_carousel

_BASE = Path(__file__).parent
_DB_PATH = _BASE / "data" / "post_history.db"
_QUEUE_PENDING = _BASE / "queue" / "pending"
_QUEUE_APPROVED = _BASE / "queue" / "approved"
_QUEUE_CURATED = _BASE / "queue" / "curated"
_GENERATED = _BASE / "Generated_Memes"
_PILLARS_DIR = _BASE / "config" / "pillars"


def _post_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]


def generate_post(
    conn,
    retries: int = 2,
    dry_run: bool = False,
) -> dict | None:
    """Generate a carousel post. Returns post_dict on success, None on total failure."""

    recent_pillar_ids = get_recent_pillar_ids(conn)
    recent_topics = get_recent_topics(conn)

    for attempt in range(1, retries + 2):
        print(f"\n--- Attempt {attempt} ---")

        pillar = select_pillar(recent_pillar_ids)
        print(f"Pillar: {pillar['name']} {pillar['emoji']}")

        print("Generating topic...")
        topic_data = generate_topic(pillar, recent_topics)
        print(f"  Topic: {topic_data['topic']}")
        print(f"  Angle: {topic_data['angle']}")
        print(f"  Hook:  {topic_data['hook']}")
        if ts := topic_data.get("trend_source"):
            print(f"  Trend: {ts}")

        print("Writing carousel slides...")
        slides = write_carousel(topic_data, pillar)

        passed, failures = run_gates(
            slides, topic_data["topic"], conn,
            trend_source=topic_data.get("trend_source"),
        )
        if not passed:
            print(f"Quality gates FAILED ({len(failures)} issues):")
            for f in failures:
                print(f"  ✗ {f}")
            if attempt <= retries:
                print("Retrying...")
                continue
            else:
                print("Max retries reached — skipping this run.")
                return None
        print(f"Quality gates passed.")

        post_id = _post_id()
        bg_dir = _GENERATED / post_id
        bg_dir.mkdir(parents=True, exist_ok=True)

        # Resolve image prompts: prefer the new list, fall back to legacy single
        raw_prompts = topic_data.get("image_prompts") or []
        if not raw_prompts and topic_data.get("dall_e_prompt"):
            raw_prompts = [topic_data["dall_e_prompt"]]
        if not raw_prompts:
            raw_prompts = [f"editorial illustration for a post about {topic_data['topic']}, "
                           f"dark navy background, cyan and green accents, no text"]

        print(f"Generating {len(raw_prompts)} background image(s)...")
        bg_paths: list[Path] = []
        for idx, prompt in enumerate(raw_prompts):
            bg_path = bg_dir / f"background_{idx+1:02d}.jpg"
            if not dry_run:
                generate_background(prompt, pillar, bg_path)
            else:
                from PIL import Image
                Image.new("RGB", (1080, 1080), color=(20, 20, 30)).save(bg_path)
            bg_paths.append(bg_path)

        print("Composing slides...")
        slide_paths = compose_carousel(bg_paths, slides, pillar, bg_dir, post_id)
        print(f"  {len(slide_paths)} slides -> {bg_dir}")

        # Repo-relative paths for GitHub raw URLs
        repo_rel_paths = [str(p.relative_to(_BASE)) for p in slide_paths]

        post = {
            "id": post_id,
            "pillar_id": pillar["id"],
            "pillar_name": pillar["name"],
            "topic": topic_data["topic"],
            "angle": topic_data["angle"],
            "hook": slides[0]["text"],
            "caption": topic_data["caption"],
            "slides": slides,
            "slide_repo_paths": repo_rel_paths,
            "dall_e_prompt": topic_data["dall_e_prompt"],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        if not dry_run:
            pending_file = _QUEUE_PENDING / f"{post_id}.json"
            _QUEUE_PENDING.mkdir(parents=True, exist_ok=True)
            pending_file.write_text(json.dumps(post, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"\nPost written to: {pending_file}")
            print("Run `python approve.py` to review and publish.")

        return post

    return None


def publish_approved_post(post: dict, dry_run: bool = False) -> str:
    """Git-add slides, push, then publish carousel. Returns ig_media_id."""
    import subprocess

    repo_paths = post["slide_repo_paths"]

    if not dry_run:
        import time
        # Pull latest remote changes first to avoid push rejection
        subprocess.run(["git", "-C", str(_BASE), "pull", "--rebase", "origin", "main"],
                       check=True)
        subprocess.run(["git", "-C", str(_BASE), "add"] + repo_paths, check=True)
        stamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ")
        result = subprocess.run(["git", "-C", str(_BASE), "commit", "-m",
                        f"carousel: {post['topic'][:50]} [{stamp}]"])
        if result.returncode != 0:
            print("  Nothing new to commit (slides may already be pushed)")
        else:
            subprocess.run(["git", "-C", str(_BASE), "push"], check=True)
        time.sleep(8)  # let GitHub CDN propagate raw URL

    media_id = publish_carousel(repo_paths, post["caption"], dry_run=dry_run)
    return media_id


def _publish_post(conn, post: dict) -> None:
    media_id = publish_approved_post(post)
    # Move pending -> posted IMMEDIATELY after IG succeeds, using os.rename
    # (atomic, no buffering) and flushing stdout so a SIGTERM from an outer
    # shell timeout can't strand an orphan. Bookkeeping happens AFTER the
    # move so a SQLite hiccup can't rewind reality.
    pending = _QUEUE_PENDING / f"{post['id']}.json"
    posted_dir = _BASE / "queue" / "posted"
    posted_dir.mkdir(parents=True, exist_ok=True)
    posted = posted_dir / f"{post['id']}.json"
    if pending.exists():
        try:
            os.replace(str(pending), str(posted))  # atomic on POSIX
        except Exception as e:
            print(f"  [WARN] failed to move pending -> posted: {type(e).__name__}: {e}",
                  flush=True)
    print(f"\nPublished: {media_id}", flush=True)
    try:
        record_post(conn, post_id=post["id"], topic=post["topic"], pillar_id=post["pillar_id"],
                    hook=post["hook"], caption=post["caption"],
                    slide_paths=post["slide_repo_paths"], ig_media_id=media_id)
        update_pillar_weights(conn)
    except Exception as e:
        print(f"  [WARN] analytics bookkeeping failed (post already published): "
              f"{type(e).__name__}: {e}", flush=True)


def _load_pillar(pillar_id: str) -> dict:
    """Load a pillar YAML by id."""
    import yaml
    for path in _PILLARS_DIR.glob("*.yaml"):
        p = yaml.safe_load(path.read_text(encoding="utf-8"))
        if p.get("id") == pillar_id:
            return p
    raise ValueError(f"Pillar not found: {pillar_id}")


def publish_next_curated(conn) -> int:
    """Pick the OLDEST post in queue/curated/, compose slides, publish.

    Curated posts skip topic-generation and slide-writing entirely — the
    content is already authored by hand (typically by Claude in a Sunday
    curation session). Only image gen + compositing + IG publish remain.

    Returns exit code (0 = success or empty-queue no-op, 1 = failure).
    """
    curated_files = sorted(_QUEUE_CURATED.glob("*.json"))
    if not curated_files:
        print("No curated posts in queue/curated/. Nothing to publish this slot.",
              flush=True)
        return 0

    src = curated_files[0]
    curated = json.loads(src.read_text(encoding="utf-8"))
    print(f"Publishing curated post: {curated.get('topic', '?')}  ({src.name})")

    pillar = _load_pillar(curated["pillar_id"])

    # Assemble a runtime post_id + directory
    post_id = _post_id()
    bg_dir = _GENERATED / post_id
    bg_dir.mkdir(parents=True, exist_ok=True)

    # Resolve images. Three sources, in this priority:
    #  1. curated.image_paths      — full set from the JSON (explicit override)
    #  2. assets/curated/<id>/cover.{jpg,png} — user-generated cover for slide 1
    #     (drop your Gemini image here and the pipeline uses it as slide 1);
    #     the rest still come from CF FLUX
    #  3. curated.image_prompts    — CF FLUX generates all N
    bg_paths: list[Path] = []
    user_paths = curated.get("image_paths") or []
    curated_id = curated.get("id") or src.stem
    cover_dir = _BASE / "assets" / "curated" / curated_id
    cover_path: Path | None = None
    for ext in ("cover.jpg", "cover.jpeg", "cover.png"):
        candidate = cover_dir / ext
        if candidate.exists():
            cover_path = candidate
            break

    if user_paths:
        for p in user_paths:
            src_img = Path(p) if Path(p).is_absolute() else _BASE / p
            if not src_img.exists():
                print(f"  [WARN] curated image_path missing: {src_img}", flush=True)
                continue
            dst = bg_dir / f"background_{len(bg_paths)+1:02d}.jpg"
            shutil.copy(str(src_img), str(dst))
            bg_paths.append(dst)
        if bg_paths:
            print(f"  Using {len(bg_paths)} user-provided image(s) from image_paths")

    if not bg_paths:
        prompts = curated.get("image_prompts") or [
            f"editorial illustration for {curated.get('topic', 'a post')}, "
            f"dark navy background, cyan and green accents, no text"
        ]
        # If a user cover.{jpg,png} exists, drop it in as slide 1's bg and
        # skip generating the first prompt. Slide 1 gets your image, slides
        # 2-7 keep the CF-generated backgrounds from the rest of the prompts.
        start_idx = 0
        if cover_path is not None:
            dst = bg_dir / "background_01.jpg"
            shutil.copy(str(cover_path), str(dst))
            bg_paths.append(dst)
            start_idx = 1
            print(f"  Using user-provided cover: {cover_path.relative_to(_BASE)}")

        remaining = prompts[start_idx:] if start_idx else prompts
        if remaining:
            print(f"  Generating {len(remaining)} image(s) via Cloudflare FLUX...")
            for prompt in remaining:
                bg = bg_dir / f"background_{len(bg_paths)+1:02d}.jpg"
                generate_background(prompt, pillar, bg)
                bg_paths.append(bg)

    # Compose slides
    print("Composing slides...")
    slide_paths = compose_carousel(bg_paths, curated["slides"], pillar, bg_dir, post_id)
    repo_rel_paths = [str(p.relative_to(_BASE)) for p in slide_paths]

    post = {
        "id": post_id,
        "pillar_id": curated["pillar_id"],
        "pillar_name": curated.get("pillar_name", pillar["name"]),
        "topic": curated["topic"],
        "angle": curated.get("angle", ""),
        "hook": curated.get("hook") or curated["slides"][0].get("text", ""),
        "caption": curated["caption"],
        "slides": curated["slides"],
        "slide_repo_paths": repo_rel_paths,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": "curated",
        "curated_file": src.name,
    }

    # Write to queue/pending so the standard publish path can pick it up
    _QUEUE_PENDING.mkdir(parents=True, exist_ok=True)
    pending_file = _QUEUE_PENDING / f"{post_id}.json"
    pending_file.write_text(json.dumps(post, indent=2, ensure_ascii=False),
                            encoding="utf-8")

    # Publish
    print("Auto-publishing curated post...", flush=True)
    _publish_post(conn, post)

    # On success: delete the curated source file AND git-commit + push that
    # deletion. Without the commit, next scheduled run checks out a fresh
    # repo, still sees the file, and re-publishes it (real bug hit in
    # production for 3 days — same "5 free AI tools" post published 5+
    # times because the runner's file delete was ephemeral).
    import subprocess
    try:
        subprocess.run(["git", "-C", str(_BASE), "rm", "-f", str(src.relative_to(_BASE))],
                       check=True, capture_output=True)
        subprocess.run(["git", "-C", str(_BASE), "commit", "-m",
                        f"queue: consume curated {src.name}"],
                       check=True, capture_output=True)
        # Pull-rebase before push in case another commit landed while we
        # were publishing to IG (slide-JPG commit from _publish_post).
        subprocess.run(["git", "-C", str(_BASE), "pull", "--rebase", "origin", "main"],
                       check=True, capture_output=True)
        subprocess.run(["git", "-C", str(_BASE), "push", "origin", "main"],
                       check=True, capture_output=True)
        print(f"  Consumed curated source: {src.name} (pushed to origin)",
              flush=True)
    except subprocess.CalledProcessError as e:
        # Fall back to plain unlink so at least the runner's own state is
        # correct; next run will still re-publish, but that's a warn not a
        # crash. IG post itself is already live.
        try:
            if src.exists():
                src.unlink()
        except Exception:
            pass
        stderr = (e.stderr or b"").decode(errors="replace")[:300]
        print(f"  [WARN] failed to git-commit curated deletion: {stderr}",
              flush=True)

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Profit Prompts content pipeline")
    parser.add_argument("--dry-run", action="store_true", help="No API calls, no queue writes")
    parser.add_argument("--publish", action="store_true", help="Auto-generate + publish (CI mode)")
    parser.add_argument("--publish-curated", action="store_true",
                        help="Publish oldest post from queue/curated/ (skips LLM ideation + writing)")
    parser.add_argument("--retry-pending", action="store_true", help="Publish oldest pending post (no regeneration)")
    parser.add_argument("--retries", type=int, default=2, help="Quality gate retry limit")
    args = parser.parse_args()

    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_db(_DB_PATH)

    if args.retry_pending:
        pending_files = sorted(_QUEUE_PENDING.glob("*.json"))
        if not pending_files:
            print("No pending posts to retry.")
            conn.close(); return
        post = json.loads(pending_files[0].read_text(encoding="utf-8"))
        print(f"Retrying pending post: {post['topic']}")
        _publish_post(conn, post)
        conn.close(); return

    if args.publish_curated:
        rc = publish_next_curated(conn)
        conn.close()
        sys.exit(rc)

    post = generate_post(conn, retries=args.retries, dry_run=args.dry_run)
    if post is None:
        sys.exit(1)

    if args.publish and not args.dry_run:
        print("\nAuto-publishing (--publish mode)...")
        _publish_post(conn, post)
    elif args.dry_run:
        print("\n[dry-run] Pipeline complete. No files written.")
        for s in post["slides"]:
            layout = s.get("layout")
            if layout == "split":
                preview = (f"[SPLIT] {s.get('left_label','?')}: {s.get('left_text','')[:30]}"
                           f" | {s.get('right_label','?')}: {s.get('right_text','')[:30]}")
            elif layout == "step":
                preview = f"[STEP {s.get('step_num','?')}] {s.get('title','')}: {s.get('body','')[:50]}"
            elif layout == "big_stat":
                preview = f"[BIG_STAT] {s.get('stat','?')} {s.get('unit','')} — {s.get('caption','')[:40]}"
            elif layout == "numbered":
                items = s.get("items", [])
                preview = f"[NUMBERED {len(items)}] " + " / ".join(f"{it.get('num','')} {it.get('title','')}" for it in items[:3])
                if len(items) > 3:
                    preview += " ..."
            else:
                preview = s.get("text", "")[:80]
            print(f"  Slide {s['slide']}: {preview}")

    conn.close()


if __name__ == "__main__":
    main()
