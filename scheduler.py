"""Step 5 - schedules the entire daily pipeline with APScheduler.

Morning generation run (produces the day's queue of memes):
    06:00  news_scraper      -> data/news_cache.json
    06:15  emotion_matcher   -> data/emotion_matched.json
    06:20  reaction_picker   -> data/reaction_selection.json
    06:30  meme_compositor   -> output/memes/*.jpg, then builds data/queue.json
           (one queued meme per configured post_time, uploads the batch + logs to Drive)

Posting run, once per configured post_time (default 08:00, 13:00, 21:00):
    Pops the next meme off data/queue.json and pushes it to Drive's
    Generated_Memes folder as the publish-ready file for that slot. Actually
    publishing to Instagram itself is a separate, deliberately out-of-scope
    step (requires Meta Business API app review) - this hands off a
    ready-to-post asset for manual or future automated publishing.

Run:
    python scheduler.py             # start the long-running scheduler
    python scheduler.py --run-now generate   # run the morning batch immediately, then exit
    python scheduler.py --run-now post       # run one posting cycle immediately, then exit
"""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

import drive_uploader
import emotion_matcher
import meme_compositor
import news_scraper
import reaction_picker
from config_loader import get_drive_service, get_logger, load_config


def _hh_mm(value: str) -> tuple[int, int]:
    hour, minute = value.split(":")
    return int(hour), int(minute)


def generate_daily_batch(cfg: dict[str, Any], logger) -> None:
    """Run steps 1-4 back to back, then build the day's posting queue."""
    dry_run = cfg["app"]["dry_run"]
    logger.info("=== Starting daily generation batch ===")

    try:
        asyncio.run(news_scraper.run_pipeline_step(cfg, logger))
    except Exception as exc:
        logger.error(f"news_scraper step failed, aborting this batch: {exc}")
        return

    try:
        emotion_matcher.run_pipeline_step(cfg, logger)
    except Exception as exc:
        logger.error(f"emotion_matcher step failed, aborting this batch: {exc}")
        return

    try:
        service = None if dry_run else get_drive_service(cfg, logger)
        reaction_picker.run_pipeline_step(cfg, logger, service=service)
    except Exception as exc:
        logger.error(f"reaction_picker step failed, aborting this batch: {exc}")
        return

    try:
        meme_paths = meme_compositor.run_pipeline_step(cfg, logger)
    except Exception as exc:
        logger.error(f"meme_compositor step failed, aborting this batch: {exc}")
        return

    build_queue(meme_paths, cfg, logger)

    service = None if dry_run else get_drive_service(cfg, logger)
    drive_uploader.upload_memes(meme_paths, cfg, logger, service=service, dry_run=dry_run)
    drive_uploader.upload_logs(cfg, logger, service=service, dry_run=dry_run)
    logger.info("=== Daily generation batch complete ===")


def build_queue(meme_paths: list[str], cfg: dict[str, Any], logger) -> None:
    """Assign freshly composited memes to the day's post_times slots and persist the queue."""
    post_times = cfg["schedule"]["post_times"]
    queue_size = cfg["schedule"]["queue_size"]

    if len(meme_paths) < queue_size:
        logger.warning(
            f"Only {len(meme_paths)} memes composited but queue_size is {queue_size} - "
            "some post_times slots will be left empty today"
        )

    queue = [
        {"post_time": post_times[i], "meme_path": meme_paths[i], "posted": False}
        for i in range(min(len(meme_paths), len(post_times)))
    ]

    queue_path = Path(cfg["paths"]["queue_file"])
    with open(queue_path, "w", encoding="utf-8") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)
    logger.info(f"Queue built with {len(queue)} entries -> {queue_path}")


def load_queue(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    queue_path = Path(cfg["paths"]["queue_file"])
    if not queue_path.exists():
        return []
    with open(queue_path, encoding="utf-8") as f:
        return json.load(f)


def save_queue(queue: list[dict[str, Any]], cfg: dict[str, Any]) -> None:
    queue_path = Path(cfg["paths"]["queue_file"])
    with open(queue_path, "w", encoding="utf-8") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)


def post_next_from_queue(cfg: dict[str, Any], logger, post_time: str) -> None:
    """Push the meme queued for this post_time slot to Drive as publish-ready."""
    dry_run = cfg["app"]["dry_run"]
    queue = load_queue(cfg)

    entry = next((e for e in queue if e["post_time"] == post_time and not e["posted"]), None)
    if entry is None:
        logger.warning(f"No pending queued meme found for post_time={post_time}")
        return

    logger.info(f"Publishing queued meme for {post_time}: {entry['meme_path']}")
    service = None if dry_run else get_drive_service(cfg, logger)
    drive_uploader.upload_memes([entry["meme_path"]], cfg, logger, service=service, dry_run=dry_run)

    entry["posted"] = True
    save_queue(queue, cfg)


def build_scheduler(cfg: dict[str, Any], logger) -> BlockingScheduler:
    try:
        from zoneinfo import ZoneInfo

        tz = ZoneInfo(cfg["app"]["timezone"])
    except Exception:
        logger.warning(f"Could not load timezone {cfg['app']['timezone']!r}, defaulting to system local time")
        tz = None

    scheduler = BlockingScheduler(timezone=tz)
    sched_cfg = cfg["schedule"]

    step_jobs = [
        ("news_fetch_time", "news_scraper", lambda: asyncio.run(news_scraper.run_pipeline_step(cfg, logger))),
        ("emotion_match_time", "emotion_matcher", lambda: emotion_matcher.run_pipeline_step(cfg, logger)),
        (
            "reaction_pick_time",
            "reaction_picker",
            lambda: reaction_picker.run_pipeline_step(
                cfg, logger, service=None if cfg["app"]["dry_run"] else get_drive_service(cfg, logger)
            ),
        ),
    ]
    for time_key, job_id, func in step_jobs:
        hour, minute = _hh_mm(sched_cfg[time_key])
        scheduler.add_job(func, CronTrigger(hour=hour, minute=minute), id=job_id, name=job_id)

    # Compositor step also finalizes the queue + uploads, so it gets its own wrapper
    # instead of calling meme_compositor.run_pipeline_step directly.
    hour, minute = _hh_mm(sched_cfg["compositor_time"])
    scheduler.add_job(
        lambda: _finalize_batch(cfg, logger),
        CronTrigger(hour=hour, minute=minute),
        id="meme_compositor_and_publish_prep",
        name="meme_compositor_and_publish_prep",
    )

    for post_time in sched_cfg["post_times"]:
        hour, minute = _hh_mm(post_time)
        scheduler.add_job(
            lambda pt=post_time: post_next_from_queue(cfg, logger, pt),
            CronTrigger(hour=hour, minute=minute),
            id=f"post_{post_time}",
            name=f"post_{post_time}",
        )

    return scheduler


def _finalize_batch(cfg: dict[str, Any], logger) -> None:
    dry_run = cfg["app"]["dry_run"]
    meme_paths = meme_compositor.run_pipeline_step(cfg, logger)
    build_queue(meme_paths, cfg, logger)
    service = None if dry_run else get_drive_service(cfg, logger)
    drive_uploader.upload_memes(meme_paths, cfg, logger, service=service, dry_run=dry_run)
    drive_uploader.upload_logs(cfg, logger, service=service, dry_run=dry_run)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the meme pipeline scheduler")
    parser.add_argument(
        "--run-now",
        choices=["generate", "post"],
        help="Run one cycle immediately instead of starting the long-running scheduler",
    )
    parser.add_argument("--post-time", help="Which post_times slot to publish when using --run-now post")
    args = parser.parse_args()

    cfg = load_config()
    logger = get_logger("scheduler", cfg)

    if args.run_now == "generate":
        generate_daily_batch(cfg, logger)
        return
    if args.run_now == "post":
        post_time = args.post_time or cfg["schedule"]["post_times"][0]
        post_next_from_queue(cfg, logger, post_time)
        return

    scheduler = build_scheduler(cfg, logger)
    logger.info("Scheduler started. Jobs:")
    for job in scheduler.get_jobs():
        logger.info(f"  {job.id}: next run {job.trigger}")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped")


if __name__ == "__main__":
    main()
