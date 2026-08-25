#!/usr/bin/env python3
"""Retime a reel's beats against the audio that was actually generated.

Beats are hand-timed in the plan against a guess at how long the VO will run.
The generated audio never matches that guess, so cards drift ahead of or behind
the voice. This snaps them to the real timings.

Two modes, per beat:

  cue   The beat carries a `cue` phrase from the VO. The beat is moved to the
        moment that phrase starts being spoken. This is the one that matters —
        it fixes *semantic* drift, not just jitter.

  snap  No cue. The beat's existing `at` is nudged to the nearest word
        boundary, so a card never appears mid-syllable.

    python scripts/snap_beats.py reels/data/<id>.reel.json [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

LEAD_IN = 0.12   # cards land a beat before the words, not after


def norm(w: str) -> str:
    return re.sub(r"[^a-z0-9]", "", w.lower())


def find_cue(captions: list[dict], cue: str) -> float | None:
    """Start time of the first word of `cue`, matched as a word sequence."""
    want = [norm(w) for w in cue.split() if norm(w)]
    if not want:
        return None
    words = [norm(c["word"]) for c in captions]
    for i in range(len(words) - len(want) + 1):
        if words[i:i + len(want)] == want:
            return captions[i]["start"]
    # Fall back to the longest leading run that does match, so a small
    # transcription difference still lands the beat roughly right.
    for n in range(len(want) - 1, 1, -1):
        head = want[:n]
        for i in range(len(words) - n + 1):
            if words[i:i + n] == head:
                return captions[i]["start"]
    return None


def nearest_word(captions: list[dict], t: float) -> float:
    return min((c["start"] for c in captions), key=lambda s: abs(s - t))


def snap(reel: dict) -> list[str]:
    captions = reel.get("captions") or []
    if not captions:
        return ["no captions — nothing to snap against"]

    duration = reel.get("durationInSeconds", captions[-1]["end"])
    log = []
    for i, beat in enumerate(reel.get("beats", [])):
        old = beat.get("at", 0.0)
        cue = beat.get("cue")

        if i == 0:
            beat["at"] = 0.0
            new, how = 0.0, "pinned to start"
        elif cue:
            hit = find_cue(captions, cue)
            if hit is None:
                new = nearest_word(captions, old)
                how = f'cue "{cue[:28]}" NOT FOUND, snapped to word'
            else:
                new = max(0.0, hit - LEAD_IN)
                how = f'cue "{cue[:28]}"'
            beat["at"] = round(new, 2)
        else:
            new = max(0.0, nearest_word(captions, old) - LEAD_IN)
            beat["at"] = round(new, 2)
            how = "nearest word"

        drift = beat["at"] - old
        log.append(f"  beat {i} {beat['type']:<6} {old:>6.2f} -> {beat['at']:>6.2f}"
                   f"  ({drift:+.2f}s)  {how}")

    # A beat past the end of the audio never appears on screen at all.
    for i, beat in enumerate(reel.get("beats", [])):
        if beat["at"] >= duration:
            log.append(f"  WARNING beat {i} at {beat['at']}s is past the "
                       f"{duration}s audio and will never show")
    return log


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("reel", help="path to a <id>.reel.json")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    p = Path(args.reel)
    if not p.exists():
        sys.exit(f"no such file: {p}")

    reel = json.loads(p.read_text(encoding="utf-8"))
    print(f"{reel['id']}  {reel.get('durationInSeconds')}s  "
          f"{len(reel.get('captions', []))} caption words")
    for line in snap(reel):
        print(line)

    if args.dry_run:
        print("\n[dry-run] not written")
    else:
        p.write_text(json.dumps(reel, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nwrote {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
