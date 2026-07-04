"""Step 3 (06:20) - pick a reaction image matching each story's emotion.

Lists images in the Drive reaction-images folder, matches them against the
requested emotion via the character_emotion_number.jpg filename pattern (or
the manual data/emotion_reaction_index.csv override), and downloads a random
match locally.

If no Drive service account is configured yet, falls back to auto-generated
local placeholder images so the rest of the pipeline (compositor, scheduler)
can still be built and tested end-to-end.

Run standalone for isolated testing:
    python reaction_picker.py --sync-index      # rebuild the CSV from live Drive
    python reaction_picker.py --emotion angry   # pick+download one image
    python reaction_picker.py                   # process data/emotion_matched.json
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import random
import re
from pathlib import Path
from typing import Any

from config_loader import get_drive_service, get_logger, load_config

FILENAME_RE = re.compile(r"^(?P<character>[A-Za-z0-9]+)_(?P<emotion>[A-Za-z]+)_(?P<number>\d+)\.\w+$")
CSV_FIELDS = ["drive_file_id", "filename", "character", "emotion", "number", "notes"]


def parse_filename(filename: str) -> dict[str, str] | None:
    match = FILENAME_RE.match(filename)
    if not match:
        return None
    return match.groupdict()


def list_drive_images(service, folder_id: str, logger) -> list[dict[str, Any]]:
    """List all image files in a Drive folder, paginating through results."""
    files: list[dict[str, Any]] = []
    page_token = None
    query = f"'{folder_id}' in parents and mimeType contains 'image/' and trashed = false"
    try:
        while True:
            response = (
                service.files()
                .list(
                    q=query,
                    fields="nextPageToken, files(id, name, mimeType)",
                    pageToken=page_token,
                    pageSize=200,
                )
                .execute()
            )
            files.extend(response.get("files", []))
            page_token = response.get("nextPageToken")
            if not page_token:
                break
    except Exception as exc:
        logger.error(f"Failed to list Drive folder {folder_id}: {exc}")
        return []
    return files


def load_csv_index(csv_path: str) -> list[dict[str, str]]:
    path = Path(csv_path)
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_csv_index(rows: list[dict[str, str]], csv_path: str) -> None:
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def sync_index(cfg: dict[str, Any], logger) -> list[dict[str, str]]:
    """Rebuild the CSV index from live Drive contents.

    Files matching character_emotion_number.<ext> are indexed automatically.
    Existing manual CSV rows whose filename isn't present in Drive are kept
    (so hand-added exceptions/notes survive a re-sync) but flagged.
    """
    service = get_drive_service(cfg, logger)
    if service is None:
        logger.error("Cannot sync index without Drive credentials - see README.md")
        return load_csv_index(cfg["reaction_index"]["csv_path"])

    folder_id = cfg["drive"]["reaction_images_folder_id"]
    drive_files = list_drive_images(service, folder_id, logger)
    logger.info(f"Found {len(drive_files)} images in reaction-images Drive folder")

    new_rows: dict[str, dict[str, str]] = {}
    unmatched = 0
    for f in drive_files:
        parsed = parse_filename(f["name"])
        if not parsed:
            unmatched += 1
            continue
        new_rows[f["name"]] = {
            "drive_file_id": f["id"],
            "filename": f["name"],
            "character": parsed["character"].lower(),
            "emotion": parsed["emotion"].lower(),
            "number": parsed["number"],
            "notes": "",
        }

    if unmatched:
        logger.warning(
            f"{unmatched} Drive file(s) didn't match the character_emotion_number pattern - "
            "add them to the CSV manually if they should be usable"
        )

    existing_rows = load_csv_index(cfg["reaction_index"]["csv_path"])
    for row in existing_rows:
        if row["filename"] not in new_rows:
            row["notes"] = (row.get("notes") or "").strip() or "not found in Drive on last sync"
            new_rows[row["filename"]] = row

    merged = list(new_rows.values())
    save_csv_index(merged, cfg["reaction_index"]["csv_path"])
    logger.info(f"Synced index: {len(merged)} total rows -> {cfg['reaction_index']['csv_path']}")
    return merged


def pick_reaction_row(
    emotion: str, index_rows: list[dict[str, str]], cfg: dict[str, Any], rng: random.Random, logger
) -> dict[str, str] | None:
    matches = [r for r in index_rows if r["emotion"].lower() == emotion.lower()]
    if not matches:
        default_emotion = cfg["emotion_rules"]["default_emotion"]
        logger.warning(f"No reaction image indexed for emotion='{emotion}' - falling back to '{default_emotion}'")
        matches = [r for r in index_rows if r["emotion"].lower() == default_emotion.lower()]
    if not matches:
        logger.error(f"No reaction images available at all for emotion='{emotion}' or the default emotion")
        return None
    return rng.choice(matches)


def download_drive_file(service, file_id: str, dest_path: Path, logger) -> bool:
    from googleapiclient.http import MediaIoBaseDownload

    try:
        request = service.files().get_media(fileId=file_id)
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        dest_path.write_bytes(buffer.getvalue())
        return True
    except Exception as exc:
        logger.error(f"Failed to download Drive file {file_id}: {exc}")
        return False


def _placeholder_image_path(emotion: str, cfg: dict[str, Any]) -> Path:
    """Generate (or reuse a cached) local placeholder reaction image.

    Used only when no Drive credentials are configured, so the compositor and
    scheduler can be exercised end-to-end without live Drive access.
    """
    from PIL import Image, ImageDraw

    cache_dir = cfg["_root"] / "data" / "sample_reactions"
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / f"placeholder_{emotion}.jpg"
    if path.exists():
        return path

    colors = {
        "skeptical": (120, 120, 150),
        "shocked": (180, 60, 60),
        "laughing": (230, 190, 40),
        "angry": (200, 40, 40),
        "excited": (40, 160, 90),
        "confused": (100, 100, 100),
    }
    color = colors.get(emotion, (90, 90, 90))
    img = Image.new("RGB", (900, 900), color=color)
    draw = ImageDraw.Draw(img)
    draw.text((40, 400), f"[{emotion.upper()}]", fill=(255, 255, 255))
    img.save(path, "JPEG")
    return path


def pick_and_download(
    emotion: str,
    cfg: dict[str, Any],
    logger,
    service=None,
    index_rows: list[dict[str, str]] | None = None,
    rng: random.Random | None = None,
) -> dict[str, Any] | None:
    rng = rng or random.Random()

    if service is None:
        path = _placeholder_image_path(emotion, cfg)
        logger.info(f"[offline] Using placeholder reaction image for '{emotion}': {path}")
        return {"emotion": emotion, "local_path": str(path), "drive_file_id": None, "filename": path.name}

    index_rows = index_rows if index_rows is not None else load_csv_index(cfg["reaction_index"]["csv_path"])
    row = pick_reaction_row(emotion, index_rows, cfg, rng, logger)
    if row is None:
        return None

    dest_dir = cfg["_root"] / "data" / "downloaded_reactions"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / row["filename"]

    if not dest_path.exists():
        ok = download_drive_file(service, row["drive_file_id"], dest_path, logger)
        if not ok:
            return None

    logger.info(f"Picked reaction image for '{emotion}': {row['filename']}")
    return {
        "emotion": emotion,
        "local_path": str(dest_path),
        "drive_file_id": row["drive_file_id"],
        "filename": row["filename"],
    }


def load_matched_stories(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    path = cfg["_root"] / "data" / "emotion_matched.json"
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []


def run_pipeline_step(cfg: dict[str, Any], logger, service=None) -> list[dict[str, Any]]:
    """Pick+download a reaction image for every matched story. Called by CLI and scheduler.py."""
    rng = random.Random()
    stories = load_matched_stories(cfg)
    if not stories:
        logger.warning("No matched stories found - run news_scraper.py and emotion_matcher.py first")
        return []

    index_rows = load_csv_index(cfg["reaction_index"]["csv_path"]) if service else None

    results = []
    for story in stories:
        picked = pick_and_download(story["emotion"], cfg, logger, service=service, index_rows=index_rows, rng=rng)
        if picked:
            results.append({**story, "reaction_image": picked})

    out_path = cfg["_root"] / "data" / "reaction_selection.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved {len(results)} story+reaction pairs -> {out_path}")
    return results


def main() -> list[dict[str, Any]]:
    parser = argparse.ArgumentParser(description="Pick reaction images matching story emotions")
    parser.add_argument("--sync-index", action="store_true", help="Rebuild the CSV index from live Drive")
    parser.add_argument("--emotion", help="Pick+download a single image for this emotion and exit")
    args = parser.parse_args()

    cfg = load_config()
    logger = get_logger("reaction_picker", cfg)

    if args.sync_index:
        sync_index(cfg, logger)
        return []

    service = get_drive_service(cfg, logger)

    if args.emotion:
        result = pick_and_download(args.emotion, cfg, logger, service=service, rng=random.Random())
        logger.info(f"Result: {result}")
        return [result] if result else []

    return run_pipeline_step(cfg, logger, service=service)


if __name__ == "__main__":
    main()
