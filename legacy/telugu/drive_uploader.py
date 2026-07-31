"""Drive integration - pushes finished memes + logs to their Drive folders.

/MemeFactory/Generated_Memes/  <- composited meme images
/MemeFactory/Logs/             <- output/logs/pipeline.log
/MemeFactory/Reaction_images/  <- read-only source, handled by reaction_picker.py

Honors config.json's app.dry_run (overridable via --dry-run/--live): in
dry-run mode nothing is actually sent to Drive, every action is only logged.

Run standalone for isolated testing:
    python drive_uploader.py --dry-run
    python drive_uploader.py --live
"""
from __future__ import annotations

import argparse
import mimetypes
from pathlib import Path
from typing import Any

from config_loader import get_drive_service, get_logger, load_config

FOLDER_MIME = "application/vnd.google-apps.folder"


def get_or_create_subfolder(service, parent_id: str, name: str, logger) -> str | None:
    query = f"'{parent_id}' in parents and name = '{name}' and mimeType = '{FOLDER_MIME}' and trashed = false"
    try:
        response = service.files().list(q=query, fields="files(id, name)").execute()
        existing = response.get("files", [])
        if existing:
            return existing[0]["id"]

        folder = (
            service.files()
            .create(body={"name": name, "mimeType": FOLDER_MIME, "parents": [parent_id]}, fields="id")
            .execute()
        )
        logger.info(f"Created Drive subfolder '{name}' under {parent_id} -> {folder['id']}")
        return folder["id"]
    except Exception as exc:
        logger.error(f"Failed to get/create Drive subfolder '{name}': {exc}")
        return None


def upload_file(service, local_path: str, parent_folder_id: str, logger) -> str | None:
    from googleapiclient.http import MediaFileUpload

    path = Path(local_path)
    mime_type, _ = mimetypes.guess_type(path.name)
    mime_type = mime_type or "application/octet-stream"

    try:
        media = MediaFileUpload(str(path), mimetype=mime_type, resumable=False)
        result = (
            service.files()
            .create(body={"name": path.name, "parents": [parent_folder_id]}, media_body=media, fields="id")
            .execute()
        )
        logger.info(f"Uploaded {path.name} -> Drive file id {result['id']}")
        return result["id"]
    except Exception as exc:
        logger.error(f"Failed to upload {path}: {exc}")
        return None


def upload_memes(
    meme_paths: list[str], cfg: dict[str, Any], logger, service=None, dry_run: bool | None = None
) -> list[str]:
    dry_run = cfg["app"]["dry_run"] if dry_run is None else dry_run

    if dry_run:
        for path in meme_paths:
            logger.info(f"[DRY-RUN] Would upload meme {path} -> Drive/MemeFactory/Generated_Memes/")
        return []

    if service is None:
        logger.error("Live upload requested but no Drive service is available - skipping meme uploads")
        return []

    folder_id = get_or_create_subfolder(
        service, cfg["drive"]["parent_folder_id"], cfg["drive"]["generated_memes_subfolder_name"], logger
    )
    if folder_id is None:
        return []

    uploaded = []
    for path in meme_paths:
        file_id = upload_file(service, path, folder_id, logger)
        if file_id:
            uploaded.append(file_id)
    return uploaded


def upload_logs(cfg: dict[str, Any], logger, service=None, dry_run: bool | None = None) -> str | None:
    dry_run = cfg["app"]["dry_run"] if dry_run is None else dry_run
    log_path = Path(cfg["paths"]["local_logs_dir"]) / "pipeline.log"

    if not log_path.exists():
        logger.warning(f"No log file found at {log_path}, nothing to upload")
        return None

    if dry_run:
        logger.info(f"[DRY-RUN] Would upload log {log_path} -> Drive/MemeFactory/Logs/")
        return None

    if service is None:
        logger.error("Live upload requested but no Drive service is available - skipping log upload")
        return None

    folder_id = get_or_create_subfolder(
        service, cfg["drive"]["parent_folder_id"], cfg["drive"]["logs_subfolder_name"], logger
    )
    if folder_id is None:
        return None
    return upload_file(service, str(log_path), folder_id, logger)


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload composited memes + logs to Drive")
    parser.add_argument("--dry-run", action="store_true", help="Force dry-run regardless of config.json")
    parser.add_argument("--live", action="store_true", help="Force live upload regardless of config.json")
    args = parser.parse_args()

    cfg = load_config()
    logger = get_logger("drive_uploader", cfg)

    dry_run = cfg["app"]["dry_run"]
    if args.dry_run:
        dry_run = True
    if args.live:
        dry_run = False

    service = None if dry_run else get_drive_service(cfg, logger)

    memes_dir = Path(cfg["paths"]["local_memes_dir"])
    meme_paths = [str(p) for ext in ("*.jpg", "*.jpeg", "*.png") for p in memes_dir.glob(ext)]
    if not meme_paths:
        logger.warning(f"No composited memes found in {memes_dir} - run meme_compositor.py first")

    upload_memes(meme_paths, cfg, logger, service=service, dry_run=dry_run)
    upload_logs(cfg, logger, service=service, dry_run=dry_run)


if __name__ == "__main__":
    main()
