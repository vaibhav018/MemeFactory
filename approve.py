"""Human approval queue CLI.

Lists all posts in queue/pending/, shows slide content, and prompts for action:
  [a] approve and publish
  [s] skip (keep in pending)
  [d] delete (discard)
  [q] quit

Usage:
  python approve.py             # interactive review
  python approve.py --list      # just list pending posts, no interaction
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

from engine.analytics.tracker import get_db, record_post, update_pillar_weights
from pipeline import publish_approved_post

_BASE = Path(__file__).parent
_PENDING = _BASE / "queue" / "pending"
_APPROVED = _BASE / "queue" / "approved"
_POSTED = _BASE / "queue" / "posted"
_DB_PATH = _BASE / "data" / "post_history.db"


def _show_post(post: dict) -> None:
    print(f"\n{'='*60}")
    print(f"ID:     {post['id']}")
    print(f"Pillar: {post['pillar_name']}")
    print(f"Topic:  {post['topic']}")
    print(f"Angle:  {post['angle']}")
    print(f"\nSLIDES:")
    for s in post["slides"]:
        print(f"  [{s['slide']}] {s.get('emoji','')} {s['text']}")
    print(f"\nCAPTION:\n{post['caption']}")
    print(f"{'='*60}")


def _list_pending() -> list[tuple[Path, dict]]:
    _PENDING.mkdir(parents=True, exist_ok=True)
    items = []
    for f in sorted(_PENDING.glob("*.json")):
        try:
            post = json.loads(f.read_text(encoding="utf-8"))
            items.append((f, post))
        except Exception as e:
            print(f"  Warning: could not read {f}: {e}")
    return items


def main() -> None:
    parser = argparse.ArgumentParser(description="Review and publish pending carousel posts")
    parser.add_argument("--list", action="store_true", help="List pending posts without interacting")
    args = parser.parse_args()

    items = _list_pending()
    if not items:
        print("No pending posts in queue/pending/")
        return

    if args.list:
        print(f"\n{len(items)} pending post(s):")
        for _, post in items:
            print(f"  - [{post['id']}] {post['pillar_name']} | {post['topic']}")
        return

    conn = get_db(_DB_PATH)
    _POSTED.mkdir(parents=True, exist_ok=True)

    for path, post in items:
        _show_post(post)
        while True:
            choice = input("\n[a]pprove+publish  [s]kip  [d]elete  [q]uit: ").strip().lower()
            if choice == "a":
                print("\nPublishing...")
                try:
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
                    shutil.move(str(path), str(_POSTED / path.name))
                    print(f"Published: {media_id}")
                    update_pillar_weights(conn)
                except Exception as e:
                    print(f"!! Publish failed: {e}")
                break
            elif choice == "s":
                print("Skipped.")
                break
            elif choice == "d":
                path.unlink()
                # also remove generated slides
                slide_dir = _BASE / "Generated_Memes" / post["id"]
                if slide_dir.exists():
                    shutil.rmtree(slide_dir)
                print("Deleted.")
                break
            elif choice == "q":
                conn.close()
                sys.exit(0)
            else:
                print("Invalid choice.")

    conn.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
