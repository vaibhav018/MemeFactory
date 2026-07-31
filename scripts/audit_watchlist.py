#!/usr/bin/env python3
"""Flag handles in config/handles_watchlist.yaml that are due for review.

Creator feeds rot fast. A handle that landed 60 days ago may have pivoted
niche, gone dead, or lost engagement. This script prints handles whose
`last_reviewed_at` is older than the audit interval (default 90 days), or
missing entirely.

Not automated — Instagram has no scraping-friendly API, so review is a
human job. This script just tells you which handles to open first.

Usage:
    python scripts/audit_watchlist.py
    python scripts/audit_watchlist.py --days 60
    python scripts/audit_watchlist.py --all      # print every handle
"""
from __future__ import annotations

import argparse
import sys
from datetime import date, datetime
from pathlib import Path

import yaml


_WATCHLIST = Path(__file__).parent.parent / "config" / "handles_watchlist.yaml"
_DEFAULT_INTERVAL_DAYS = 90


def _parse_date(v) -> date | None:
    if isinstance(v, date):
        return v
    if isinstance(v, str):
        try:
            return datetime.fromisoformat(v).date()
        except ValueError:
            return None
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Watchlist audit reminder")
    parser.add_argument("--days", type=int, default=_DEFAULT_INTERVAL_DAYS,
                        help="Flag handles unreviewed for this many days (default 90)")
    parser.add_argument("--all", action="store_true",
                        help="Print every handle regardless of review age")
    args = parser.parse_args()

    if not _WATCHLIST.exists():
        print(f"ERROR: {_WATCHLIST} not found", file=sys.stderr)
        return 1
    data = yaml.safe_load(_WATCHLIST.read_text(encoding="utf-8")) or {}
    handles = data.get("handles", []) or []
    if not handles:
        print("(watchlist is empty)")
        return 0

    today = date.today()
    rows: list[tuple[int | None, str, str, list[str]]] = []
    for h in handles:
        handle = h.get("handle", "?")
        reviewed = _parse_date(h.get("last_reviewed_at"))
        pillars = h.get("pillar_affinity") or []
        if reviewed is None:
            age_days = None  # never reviewed
        else:
            age_days = (today - reviewed).days
        rows.append((age_days, handle, reviewed.isoformat() if reviewed else "(never)", pillars))

    # sort: "never" first, then oldest reviewed first
    rows.sort(key=lambda r: (0 if r[0] is None else 1, -(r[0] or 0)))

    to_show = rows if args.all else [r for r in rows if r[0] is None or r[0] >= args.days]
    if not to_show:
        print(f"All {len(rows)} handles reviewed within the last {args.days} days. Nothing to audit.")
        return 0

    print(f"Handles due for review (>{args.days} days old, or never reviewed):")
    print(f"  {'handle':32} {'last_reviewed':>14}  {'age':>7}   pillars")
    print("  " + "-" * 74)
    for age, handle, reviewed_str, pillars in to_show:
        age_str = f"{age}d" if age is not None else "never"
        pillar_str = ", ".join(pillars)
        print(f"  @{handle:31} {reviewed_str:>14}  {age_str:>7}   {pillar_str}")

    print(f"\n{len(to_show)} of {len(rows)} handles need a look.")
    print("When done: update `last_reviewed_at: YYYY-MM-DD` in "
          "config/handles_watchlist.yaml (or remove/replace the handle).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
