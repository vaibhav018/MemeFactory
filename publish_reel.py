#!/usr/bin/env python3
"""Render the next queued reel and publish it to Instagram.

Counterpart to pipeline.py, which handles carousels. Deliberately separate:
a broken Remotion render must not be able to take the carousel slot down
with it, and the two have almost nothing in common past the publish call.

Flow:
    reels/data/<id>.reel.json   (committed by the Colab voice batch)
        -> npx remotion render  -> Generated_Reels/<id>.mp4
        -> git commit + push    (Instagram fetches over https, so it must
                                 exist publicly before the container call)
        -> publish_reel()
        -> mark consumed

    python publish_reel.py [--dry-run] [--id <reel-id>] [--keep]
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dotenv import load_dotenv  # noqa: E402

BASE = Path(__file__).resolve().parent
load_dotenv(BASE / ".env")

REELS = BASE / "reels"
DATA = REELS / "data"
POSTED = DATA / "posted"
OUT_DIR = BASE / "Generated_Reels"
TIMEOUT = 1500  # render ceiling, under the workflow's own limit


# Fixtures that live in reels/data for local testing. They must never be
# picked up as publishable work — demo.reel.json has no audio and would
# otherwise be first in sort order every single day.
FIXTURES = {"demo", "example", "sample", "test"}


def _tool(*names: str) -> str:
    """Resolve an executable without assuming PATH shape across OSes."""
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    sys.exit(f"{names[0]} not found on PATH")


def pick_reel(explicit: str = "") -> Path:
    """Oldest unposted reel.json by filename, matching the curated-queue rule."""
    if explicit:
        p = DATA / f"{explicit}.reel.json"
        if not p.exists():
            sys.exit(f"no such reel: {p}")
        return p
    candidates = sorted(
        p for p in DATA.glob("*.reel.json")
        if p.is_file() and p.name.removesuffix(".reel.json") not in FIXTURES
    )
    if not candidates:
        sys.exit("no reels queued in reels/data/ — run the Colab voice notebook")
    return candidates[0]


def render(reel_path: Path, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [_tool("npx.cmd", "npx"), "remotion", "render", "Reel", str(out),
           f"--props={reel_path}"]
    print(f"  {' '.join(cmd)}")
    r = subprocess.run(cmd, cwd=REELS, timeout=TIMEOUT)
    if r.returncode != 0:
        sys.exit(f"remotion render failed ({r.returncode})")
    if not out.exists():
        sys.exit("render reported success but produced no file")
    print(f"  rendered {out.name}  {out.stat().st_size // 1024} KB")


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run([_tool("git", "git.exe"), *args], cwd=BASE, check=check,
                          capture_output=True, text=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="Render and commit, but do not publish")
    ap.add_argument("--id", default="", help="Publish this reel id specifically")
    ap.add_argument("--keep", action="store_true",
                    help="Leave the reel.json in the queue after publishing")
    args = ap.parse_args()

    reel_path = pick_reel(args.id)
    reel = json.loads(reel_path.read_text(encoding="utf-8"))
    rid = reel["id"]
    print(f"Reel: {rid}  ({reel['durationInSeconds']}s, "
          f"{len(reel['captions'])} caption words, {len(reel['beats'])} beats)")

    # An empty audioSrc resolves to reels/public/ itself, which exists — so
    # check the field before checking the file, or a voiceless reel sails
    # straight through to Instagram.
    if not reel.get("audioSrc"):
        sys.exit(f"{reel_path.name} has no audioSrc — it has not been through "
                 f"the Colab voice batch yet.")
    audio = REELS / "public" / reel["audioSrc"]
    if not audio.is_file():
        sys.exit(f"audio missing: {audio}\n"
                 f"Commit the mp3 from the Colab batch before publishing.")

    out = OUT_DIR / f"{rid}.mp4"
    print("Rendering...")
    render(reel_path, out)

    rel = out.relative_to(BASE).as_posix()

    # Instagram fetches the MP4 over https, so it has to be pushed first.
    print("Pushing render...")
    git("add", rel)
    status = git("status", "--porcelain", rel).stdout.strip()
    if status:
        git("commit", "-m", f"reel: {rid} [{datetime.now(timezone.utc):%Y-%m-%dT%H:%MZ}]")
        push = git("push", "origin", "HEAD", check=False)
        if push.returncode != 0:
            sys.exit(f"push failed, refusing to publish an unreachable url:\n{push.stderr}")
        print("  pushed")
    else:
        print("  nothing to commit (already pushed)")

    from engine.publish.instagram_client import publish_reel

    caption = reel.get("caption") or ""
    if not caption:
        hook = next((b for b in reel["beats"] if b["type"] == "hook"), None)
        caption = hook["text"] if hook else rid
        print("  no caption in reel.json — falling back to the hook text")

    media_id = publish_reel(rel, caption, dry_run=args.dry_run)

    if not args.dry_run and not args.keep:
        POSTED.mkdir(parents=True, exist_ok=True)
        reel_path.rename(POSTED / reel_path.name)
        git("add", "-A", str(DATA.relative_to(BASE).as_posix()))
        git("commit", "-m", f"queue: consume reel {rid}", check=False)
        git("push", "origin", "HEAD", check=False)
        print(f"  consumed {reel_path.name}")

    print(f"\nDone: {media_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
