#!/usr/bin/env python3
"""Publish a roundup carousel built by scripts/build_roundup.py.

    python publish_roundup.py Generated_Memes/<id>/carousel.json [--dry-run]

Instagram fetches every slide over HTTP from the repo's raw URLs, so the
slides must be committed AND pushed before this runs. A local file that is
not on the remote yields a 404 that the Graph API reports as error 9004,
"Only photo or video can be accepted as media type" — which sends you looking
at the media type instead of at the URL. Checked up front here for that reason.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

from dotenv import load_dotenv  # noqa: E402

from engine.publish.instagram_client import publish_carousel  # noqa: E402


def _git() -> str:
    found = shutil.which("git")
    if found:
        return found
    for d in (Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Git" / "cmd",
              Path("/usr/bin"), Path("/usr/local/bin")):
        for name in ("git.exe", "git"):
            if (d / name).exists():
                return str(d / name)
    sys.exit("git not found")


def ensure_pushed(paths: list[str]) -> None:
    """Refuse to publish slides the remote cannot serve."""
    git = _git()
    dirty = subprocess.run([git, "status", "--porcelain"] + paths,
                           cwd=BASE, capture_output=True, text=True).stdout.strip()
    if dirty:
        sys.exit("uncommitted slides — commit and push first:\n" + dirty)

    subprocess.run([git, "fetch", "-q"], cwd=BASE, capture_output=True, text=True)
    ahead = subprocess.run([git, "rev-list", "--count", "@{u}..HEAD"],
                           cwd=BASE, capture_output=True, text=True).stdout.strip()
    if ahead and ahead != "0":
        sys.exit(f"{ahead} unpushed commit(s) — push before publishing, or "
                 f"Instagram will 404 on every slide")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    load_dotenv(BASE / ".env")
    spec = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    slides, caption = spec["slides"], spec["caption"]

    missing = [s for s in slides if not (BASE / s).exists()]
    if missing:
        sys.exit("missing slide files:\n  " + "\n  ".join(missing))

    kinds = ["VIDEO" if s.lower().endswith((".mp4", ".mov")) else "IMAGE" for s in slides]
    print(f"{spec['id']}: {len(slides)} slides — {' '.join(kinds)}")

    if not args.dry_run:
        ensure_pushed(slides)

    media_id = publish_carousel(slides, caption, dry_run=args.dry_run)
    print(f"\npublished: {media_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
