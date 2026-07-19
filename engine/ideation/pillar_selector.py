"""Weighted round-robin pillar selector with recency penalty.

Loads all YAML pillar configs, penalizes recently-used pillars, and returns
the next pillar to post. Weights are updated by the analytics feedback loop
(analytics/tracker.py) based on shares-per-reach performance.
"""
from __future__ import annotations

import random
from pathlib import Path

import yaml


_PILLARS_DIR = Path(__file__).parent.parent.parent / "config" / "pillars"


def _load_pillars() -> list[dict]:
    pillars = []
    for path in sorted(_PILLARS_DIR.glob("*.yaml")):
        with open(path, encoding="utf-8") as f:
            pillars.append(yaml.safe_load(f))
    return pillars


def select_pillar(recent_pillar_ids: list[str]) -> dict:
    """Return a pillar dict. Penalizes pillars used in recent_pillar_ids."""
    pillars = _load_pillars()
    weights = []
    for p in pillars:
        w = p.get("weight", 1.0)
        # halve weight for each appearance in the last 3 posts
        penalty = recent_pillar_ids[:3].count(p["id"])
        w = w * (0.5 ** penalty)
        weights.append(max(w, 0.05))  # floor so nothing is completely excluded

    chosen = random.choices(pillars, weights=weights, k=1)[0]
    return chosen
