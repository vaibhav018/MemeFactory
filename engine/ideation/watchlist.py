"""Load config/handles_watchlist.yaml and expose per-pillar reference handles.

Instagram has no practical public API, so this file is signal not scraping.
Each handle carries a pillar_affinity list; get_pillar_reference_handles(pid)
returns the (at most N) handles that name `pid` as an affinity.

The topic_generator uses these to give Claude a small style anchor without
telling it to copy — 3-4 handles per pillar is enough to shape voice without
crowding the prompt.
"""
from __future__ import annotations

from pathlib import Path

import yaml


_WATCHLIST_PATH = Path(__file__).parent.parent.parent / "config" / "handles_watchlist.yaml"


def _load() -> list[dict]:
    if not _WATCHLIST_PATH.exists():
        return []
    try:
        data = yaml.safe_load(_WATCHLIST_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []
    return (data or {}).get("handles", []) or []


def get_pillar_reference_handles(pillar_id: str, limit: int = 4) -> list[dict]:
    """Return handles whose pillar_affinity contains pillar_id, capped at limit.

    Order preserved from the YAML so the file itself is the ranking. Missing
    file or malformed entries return an empty list — never raises.
    """
    handles = _load()
    matches = [h for h in handles if pillar_id in (h.get("pillar_affinity") or [])]
    return matches[:limit]
