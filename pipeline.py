"""Modern Mastery — Instagram carousel content pipeline.

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
_GENERATED = _BASE / "Generated_Memes"


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

        print("Writing carousel slides...")
        slides = write_carousel(topic_data, pillar)

        passed, failures = run_gates(slides, topic_data["topic"], conn)
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

        print("Generating background image...")
        bg_path = bg_dir / "background.jpg"
        if not dry_run:
            generate_background(topic_data["dall_e_prompt"], pillar, bg_path)
        else:
            # placeholder for dry-run
            from PIL import Image, ImageDraw
            img = Image.new("RGB", (1080, 1080), color=(20, 20, 30))
            img.save(bg_path)

        print("Composing slides...")
        slide_paths = compose_carousel(bg_path, slides, pillar, bg_dir, post_id)
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
        # Stage and push images
        subprocess.run(["git", "-C", str(_BASE), "add"] + repo_paths, check=True)
        stamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ")
        subprocess.run(["git", "-C", str(_BASE), "commit", "-m",
                        f"carousel: {post['topic'][:50]} [{stamp}]"], check=True)
        subprocess.run(["git", "-C", str(_BASE), "push"], check=True)
        import time; time.sleep(5)  # let GitHub CDN propagate

    media_id = publish_carousel(repo_paths, post["caption"], dry_run=dry_run)
    return media_id


def main() -> None:
    parser = argparse.ArgumentParser(description="Modern Mastery content pipeline")
    parser.add_argument("--dry-run", action="store_true", help="No API calls, no queue writes")
    parser.add_argument("--publish", action="store_true", help="Auto-approve and publish (CI mode)")
    parser.add_argument("--retries", type=int, default=2, help="Quality gate retry limit")
    args = parser.parse_args()

    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_db(_DB_PATH)

    post = generate_post(conn, retries=args.retries, dry_run=args.dry_run)
    if post is None:
        sys.exit(1)

    if args.publish and not args.dry_run:
        print("\nAuto-publishing (--publish mode)...")
        media_id = publish_approved_post(post)
        record_post(
            conn,
            post_id=post["id"],
            topic=post["topic"],
            pillar_id=post["pillar_id"],
            hook=post["hook"],
            caption=post["caption"],
            slide_paths=post["slide_repo_paths"],
            ig_media_id=media_id,
        )
        # Move from pending to posted
        pending = _QUEUE_PENDING / f"{post['id']}.json"
        posted = _BASE / "queue" / "posted" / f"{post['id']}.json"
        if pending.exists():
            shutil.move(str(pending), str(posted))
        print(f"\nPublished: {media_id}")
        update_pillar_weights(conn)
    elif args.dry_run:
        print("\n[dry-run] Pipeline complete. No files written.")
        # show slide texts
        for s in post["slides"]:
            print(f"  Slide {s['slide']}: {s['text'][:80]}")

    conn.close()


if __name__ == "__main__":
    main()
