"""Weighted round-robin pillar selector with recency penalty + trend momentum.

Loads all YAML pillar configs, penalizes recently-used pillars, boosts
pillars that have hot fresh trends right now, and returns the next pillar
to post. The static weight in each YAML is the baseline; analytics/tracker
adjusts it based on shares-per-reach; momentum layers on top.

Weight = base_weight × (0.5 ^ recency_count) × (1 + momentum_bonus)

momentum_bonus is 0..1: it caps out when the pillar's sources have 10+
fresh (<48h) trend items — enough hot signal to justify posting sooner.
Pillars with no wired trend sources always get momentum_bonus = 0.
"""
from __future__ import annotations

import random
from pathlib import Path

import yaml

from engine.trends.fetch import get_pillar_candidates, get_trend_age_hours


_PILLARS_DIR = Path(__file__).parent.parent.parent / "config" / "pillars"
_MOMENTUM_FRESH_HOURS = 48.0
_MOMENTUM_SATURATION = 10  # fresh trends needed to hit the +1.0 max bonus


def _load_pillars() -> list[dict]:
    pillars = []
    for path in sorted(_PILLARS_DIR.glob("*.yaml")):
        with open(path, encoding="utf-8") as f:
            pillars.append(yaml.safe_load(f))
    return pillars


def _momentum_bonus(pillar_id: str) -> float:
    """Fraction (0..1) of _MOMENTUM_SATURATION fresh trends in this pillar's feeds."""
    try:
        candidates = get_pillar_candidates(pillar_id, limit=_MOMENTUM_SATURATION * 2)
    except Exception:
        return 0.0
    if not candidates:
        return 0.0
    fresh = 0
    for c in candidates:
        age = get_trend_age_hours(c.get("title", ""))
        if age is not None and age <= _MOMENTUM_FRESH_HOURS:
            fresh += 1
    return min(fresh / _MOMENTUM_SATURATION, 1.0)


def select_pillar(recent_pillar_ids: list[str]) -> dict:
    """Return a pillar dict. Penalizes recent pillars, boosts trending ones."""
    pillars = _load_pillars()
    weights = []
    for p in pillars:
        base = p.get("weight", 1.0)
        recency = recent_pillar_ids[:3].count(p["id"])
        recency_factor = 0.5 ** recency
        momentum = _momentum_bonus(p["id"])
        w = base * recency_factor * (1.0 + momentum)
        weights.append(max(w, 0.05))  # floor so nothing is completely excluded

    chosen = random.choices(pillars, weights=weights, k=1)[0]
    return chosen
