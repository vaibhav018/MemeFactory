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


# Fixtures live in reels/data for local testing and must never be picked up as
# publishable work. Matched as a prefix, not an exact id: an exact-match set
# let "demo-curated" through, which would have published a test clip.
# Real jobs are date-stamped (20260826_13), so this cannot swallow one.
FIXTURE_PREFIXES = ("demo", "example", "sample", "test")


def _is_fixture(job_id: str) -> bool:
    return job_id.lower().startswith(FIXTURE_PREFIXES)


def _tool(*names: str) -> str:
    """Resolve an executable without assuming PATH shape across OSes."""
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    sys.exit(f"{names[0]} not found on PATH")


# Two formats share this queue and this publisher. The suffix picks the
# Remotion composition; nothing else differs downstream.
FORMATS = {".reel.json": "Reel", ".curated.json": "Curated"}


def _job_id(p: Path) -> str:
    for suffix in FORMATS:
        if p.name.endswith(suffix):
            return p.name[: -len(suffix)]
    return p.stem


def pick_job(explicit: str = "") -> tuple[Path, str]:
    """Oldest unposted job by filename. Returns (path, composition id)."""
    candidates = sorted(
        p for suffix in FORMATS for p in DATA.glob(f"*{suffix}")
        if p.is_file() and not _is_fixture(_job_id(p))
    )
    if explicit:
        candidates = [p for p in candidates if _job_id(p) == explicit]
        if not candidates:
            sys.exit(f"no queued job with id {explicit!r} in {DATA}")

    if not candidates:
        sys.exit("nothing queued in reels/data/ — run the Colab voice notebook "
                 "for a Reel, or add a <id>.curated.json for a curated clip")

    chosen = candidates[0]
    comp = next(c for s, c in FORMATS.items() if chosen.name.endswith(s))
    return chosen, comp


def render(job_path: Path, out: Path, composition: str) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [_tool("npx.cmd", "npx"), "remotion", "render", composition, str(out),
           f"--props={job_path}"]
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

    job_path, composition = pick_job(args.id)
    reel = json.loads(job_path.read_text(encoding="utf-8"))
    rid = reel["id"]

    if composition == "Reel":
        print(f"Reel: {rid}  ({reel['durationInSeconds']}s, "
              f"{len(reel['captions'])} caption words, {len(reel['beats'])} beats)")
        # An empty audioSrc resolves to reels/public/ itself, which exists — so
        # check the field before checking the file, or a voiceless reel sails
        # straight through to Instagram.
        if not reel.get("audioSrc"):
            sys.exit(f"{job_path.name} has no audioSrc — it has not been through "
                     f"the Colab voice batch yet.")
        asset = REELS / "public" / reel["audioSrc"]
        if not asset.is_file():
            sys.exit(f"audio missing: {asset}\n"
                     f"Commit the mp3 from the Colab batch before publishing.")
    else:
        credit = (reel.get("credit") or {}).get("name")
        print(f"Curated: {rid}  ({reel['durationInSeconds']}s, "
              f"credit: {credit or 'NONE'})")
        if not reel.get("videoSrc"):
            sys.exit(f"{job_path.name} has no videoSrc")
        asset = REELS / "public" / reel["videoSrc"]
        if not asset.is_file():
            sys.exit(f"source clip missing: {asset}")
        # Republishing someone's clip uncredited is the one failure here that
        # cannot be undone after the fact, so it is a hard stop rather than a
        # warning nobody reads in a cron log.
        if not credit:
            sys.exit(f"{job_path.name} has no credit.name — refusing to publish "
                     f"someone else's clip without crediting them.")

    out = OUT_DIR / f"{rid}.mp4"
    print(f"Rendering ({composition})...")
    render(job_path, out, composition)

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
        if composition == "Reel":
            hook = next((b for b in reel.get("beats", []) if b["type"] == "hook"), None)
            caption = hook["text"] if hook else rid
        else:
            caption = reel.get("commentary", "").replace("**", "")
        print("  no caption field — derived one from the content")

    if composition == "Curated":
        # The on-screen credit reaches viewers; the caption tag reaches the
        # creator, who often reshares. Only one of those is free distribution.
        tag = (reel.get("credit") or {}).get("name", "")
        if tag and tag not in caption:
            caption = f"{caption}\n\nFull credit to {tag} for the clip."

    media_id = publish_reel(rel, caption, dry_run=args.dry_run)

    if not args.dry_run and not args.keep:
        POSTED.mkdir(parents=True, exist_ok=True)
        job_path.rename(POSTED / job_path.name)
        git("add", "-A", str(DATA.relative_to(BASE).as_posix()))
        git("commit", "-m", f"queue: consume reel {rid}", check=False)
        git("push", "origin", "HEAD", check=False)
        print(f"  consumed {job_path.name}")

    print(f"\nDone: {media_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
