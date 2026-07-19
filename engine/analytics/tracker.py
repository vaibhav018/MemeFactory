"""SQLite-backed post history + performance tracking.

Schema:
  posts(id, topic, pillar_id, hook, caption, slide_paths_json, posted_at,
        ig_media_id, likes, comments, shares, saves, reach, impressions,
        saves_per_reach, shares_per_reach, updated_at)

The feedback loop in update_pillar_weights() adjusts pillar YAML weights
based on shares_per_reach performance relative to the global mean.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import yaml


_PILLARS_DIR = Path(__file__).parent.parent.parent / "config" / "pillars"


def get_db(db_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id TEXT PRIMARY KEY,
            topic TEXT NOT NULL,
            pillar_id TEXT NOT NULL,
            hook TEXT,
            caption TEXT,
            slide_paths_json TEXT,
            posted_at TEXT,
            ig_media_id TEXT,
            likes INTEGER DEFAULT 0,
            comments INTEGER DEFAULT 0,
            shares INTEGER DEFAULT 0,
            saves INTEGER DEFAULT 0,
            reach INTEGER DEFAULT 0,
            impressions INTEGER DEFAULT 0,
            saves_per_reach REAL DEFAULT 0.0,
            shares_per_reach REAL DEFAULT 0.0,
            updated_at TEXT
        )
    """)
    conn.commit()
    return conn


def record_post(conn: sqlite3.Connection, post_id: str, topic: str, pillar_id: str,
                hook: str, caption: str, slide_paths: list[str],
                ig_media_id: str = "") -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn.execute("""
        INSERT OR REPLACE INTO posts
          (id, topic, pillar_id, hook, caption, slide_paths_json, posted_at, ig_media_id, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (post_id, topic, pillar_id, hook, caption,
          json.dumps(slide_paths), now, ig_media_id, now))
    conn.commit()


def update_metrics(conn: sqlite3.Connection, post_id: str, metrics: dict) -> None:
    reach = metrics.get("reach", 0)
    saves = metrics.get("saves", 0)
    shares = metrics.get("shares", 0)
    conn.execute("""
        UPDATE posts SET
          likes=?, comments=?, shares=?, saves=?, reach=?, impressions=?,
          saves_per_reach=?, shares_per_reach=?, updated_at=?
        WHERE id=?
    """, (
        metrics.get("likes", 0), metrics.get("comments", 0),
        shares, saves, reach, metrics.get("impressions", 0),
        saves / max(reach, 1), shares / max(reach, 1),
        datetime.now(timezone.utc).isoformat(), post_id,
    ))
    conn.commit()


def get_recent_pillar_ids(conn: sqlite3.Connection, n: int = 5) -> list[str]:
    rows = conn.execute(
        "SELECT pillar_id FROM posts WHERE posted_at IS NOT NULL ORDER BY posted_at DESC LIMIT ?", (n,)
    ).fetchall()
    return [r["pillar_id"] for r in rows]


def get_recent_topics(conn: sqlite3.Connection, n: int = 20) -> list[str]:
    rows = conn.execute(
        "SELECT topic FROM posts ORDER BY posted_at DESC LIMIT ?", (n,)
    ).fetchall()
    return [r["topic"] for r in rows]


def update_pillar_weights(conn: sqlite3.Connection) -> None:
    """Adjust YAML weights based on each pillar's mean shares_per_reach vs global mean."""
    rows = conn.execute("""
        SELECT pillar_id, AVG(shares_per_reach) as mean_spr, COUNT(*) as n
        FROM posts WHERE reach > 100
        GROUP BY pillar_id
    """).fetchall()

    if not rows:
        return

    global_mean = sum(r["mean_spr"] for r in rows) / len(rows)
    if global_mean == 0:
        return

    for row in rows:
        if row["n"] < 3:  # need at least 3 posts for signal
            continue
        ratio = row["mean_spr"] / global_mean
        new_weight = max(0.2, min(3.0, ratio))  # clamp to [0.2, 3.0]

        pillar_id = row["pillar_id"]
        for path in _PILLARS_DIR.glob("*.yaml"):
            with open(path, encoding="utf-8") as f:
                cfg = yaml.safe_load(f)
            if cfg.get("id") == pillar_id:
                cfg["weight"] = round(new_weight, 2)
                with open(path, "w", encoding="utf-8") as f:
                    yaml.dump(cfg, f, allow_unicode=True, sort_keys=False)
                print(f"  [feedback] {pillar_id} weight → {new_weight:.2f}")
                break
