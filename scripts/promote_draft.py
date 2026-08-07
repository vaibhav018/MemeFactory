"""
Promote an approved draft from queue/curated_draft/ into the scheduled queue.

Takes a draft_id and a target slot (YYYYMMDD_HH) and:
  1. Renames queue/curated_draft/<draft_id>.json → queue/curated/<slot>.json
     (updating the "id" field inside the JSON to match).
  2. Moves assets/curated_draft/<draft_id>/cover.jpg → assets/curated/<slot>/cover.jpg
     so pipeline.py's user-cover convention kicks in (slide 1 = the swiped image).
  3. git-adds both paths so you can commit + push in one motion.

Usage:
  python scripts/promote_draft.py swipe_wealthpill_ab12cd 20260810_05
  python scripts/promote_draft.py swipe_wealthpill_ab12cd 20260810_14 --commit
  python scripts/promote_draft.py --list      # show all pending drafts

Slot format:
  YYYYMMDD_HH where HH is 05 (morning ~11:00 IST) or 14 (evening ~19:30 IST).
  Cron in .github/workflows/profit_prompts.yml drives which slot fires when.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


BASE = Path(__file__).resolve().parents[1]
DRAFT_DIR = BASE / "queue" / "curated_draft"
DRAFT_ASSETS_DIR = BASE / "assets" / "curated_draft"
CURATED_DIR = BASE / "queue" / "curated"
CURATED_ASSETS_DIR = BASE / "assets" / "curated"

SLOT_RE = re.compile(r"^\d{8}_(05|14)$")


def list_drafts() -> int:
    if not DRAFT_DIR.exists():
        print("No drafts — queue/curated_draft/ does not exist yet.")
        return 0
    drafts = sorted(DRAFT_DIR.glob("*.json"))
    if not drafts:
        print("No drafts pending.")
        return 0
    print(f"{len(drafts)} draft(s) in {DRAFT_DIR.relative_to(BASE)}/\n")
    for path in drafts:
        try:
            data = json.loads(path.read_text())
        except Exception:
            print(f"  {path.stem}  [unreadable]")
            continue
        src = data.get("source", {})
        cover = "✓" if (DRAFT_ASSETS_DIR / path.stem / "cover.jpg").exists() else "—"
        print(f"  [{cover}] {path.stem}")
        print(f"       topic:  {data.get('topic', '?')}")
        print(f"       from:   @{src.get('handle', '?')}  ({src.get('likes', 0)}❤ + {src.get('comments', 0)}💬)")
        print(f"       url:    {src.get('url', '?')}\n")
    return 0


def validate_slot(slot: str) -> None:
    if not SLOT_RE.match(slot):
        sys.exit(f"Slot {slot!r} must match YYYYMMDD_HH where HH is 05 or 14.")
    try:
        datetime.strptime(slot[:8], "%Y%m%d")
    except ValueError:
        sys.exit(f"Slot {slot!r} — {slot[:8]} is not a valid date.")


def promote(draft_id: str, slot: str, commit: bool = False) -> int:
    validate_slot(slot)

    src_json = DRAFT_DIR / f"{draft_id}.json"
    if not src_json.exists():
        sys.exit(f"Draft not found: {src_json.relative_to(BASE)}")

    dst_json = CURATED_DIR / f"{slot}.json"
    if dst_json.exists():
        sys.exit(f"Slot already filled: {dst_json.relative_to(BASE)} — pick another slot.")

    # Load + rewrite id, then write to destination.
    data = json.loads(src_json.read_text())
    data["id"] = slot
    data.setdefault("source", {})["promoted_from_draft"] = draft_id
    data["source"]["promoted_at"] = datetime.utcnow().isoformat() + "Z"

    dst_json.parent.mkdir(parents=True, exist_ok=True)
    dst_json.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"  ✓ JSON  → {dst_json.relative_to(BASE)}")

    # Move cover image if present.
    src_cover = DRAFT_ASSETS_DIR / draft_id / "cover.jpg"
    dst_cover = None
    if src_cover.exists():
        dst_cover_dir = CURATED_ASSETS_DIR / slot
        dst_cover_dir.mkdir(parents=True, exist_ok=True)
        dst_cover = dst_cover_dir / "cover.jpg"
        shutil.copy(str(src_cover), str(dst_cover))
        print(f"  ✓ cover → {dst_cover.relative_to(BASE)}")
    else:
        print(f"  — no cover for {draft_id} — slide 1 will use CF FLUX fallback")

    # Clean up draft artefacts so the same draft can't be double-promoted.
    src_json.unlink()
    if src_cover.exists():
        src_cover.unlink()
        # Remove empty draft asset dir.
        draft_asset_parent = DRAFT_ASSETS_DIR / draft_id
        if draft_asset_parent.exists() and not any(draft_asset_parent.iterdir()):
            draft_asset_parent.rmdir()

    # Stage for git so user can commit in one motion.
    paths_to_add = [str(dst_json.relative_to(BASE))]
    if dst_cover:
        paths_to_add.append(str(dst_cover.relative_to(BASE)))
    subprocess.run(["git", "-C", str(BASE), "add", *paths_to_add], check=False)
    print(f"  ✓ git-added: {', '.join(paths_to_add)}")

    if commit:
        msg = f"curated: promote {draft_id} → {slot}"
        r = subprocess.run(["git", "-C", str(BASE), "commit", "-m", msg], capture_output=True, text=True)
        if r.returncode == 0:
            print(f"  ✓ committed: {msg}")
        else:
            print(f"  [warn] commit failed: {r.stderr.strip()}")

    print(f"\nDone. Next: git push (or re-run with --commit next time).")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("draft_id", nargs="?", help="Draft filename (without .json)")
    ap.add_argument("slot", nargs="?", help="Target slot YYYYMMDD_HH (HH = 05 or 14)")
    ap.add_argument("--list", action="store_true", help="Show pending drafts and exit")
    ap.add_argument("--commit", action="store_true", help="Also git-commit after staging")
    args = ap.parse_args()

    if args.list:
        return list_drafts()
    if not args.draft_id or not args.slot:
        ap.print_help()
        return 1
    return promote(args.draft_id, args.slot, commit=args.commit)


if __name__ == "__main__":
    sys.exit(main())
