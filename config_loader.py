"""Shared config loading + logging setup for every pipeline module.

Every script in this project calls `load_config()` instead of reading
config.json directly, so path resolution and secret-loading stay in one place.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
CONFIG_PATH = PROJECT_ROOT / "config.json"


class ConfigError(RuntimeError):
    pass


def _resolve(path_str: str) -> Path:
    """Resolve a config path relative to the project root (never the CWD)."""
    p = Path(path_str)
    return p if p.is_absolute() else (PROJECT_ROOT / p)


def load_config() -> dict[str, Any]:
    """Load config.json, merge in .env secrets, and resolve all file paths.

    Adds a `_root` key (Path) and rewrites known path-like fields to absolute
    paths so downstream modules never hardcode or re-derive locations.
    """
    load_dotenv(PROJECT_ROOT / ".env")

    if not CONFIG_PATH.exists():
        raise ConfigError(f"config.json not found at {CONFIG_PATH}")

    with open(CONFIG_PATH, encoding="utf-8") as f:
        cfg = json.load(f)

    cfg["_root"] = PROJECT_ROOT

    # Secrets: pulled from environment, never stored in config.json itself.
    newsdataio_key_env = cfg["news"]["newsdataio_key_env"]
    cfg["news"]["newsdataio_key"] = os.environ.get(newsdataio_key_env, "")

    # Resolve Drive credential paths.
    cfg["drive"]["service_account_file"] = str(_resolve(cfg["drive"]["service_account_file"]))
    cfg["drive"]["oauth_client_secret_file"] = str(_resolve(cfg["drive"]["oauth_client_secret_file"]))
    cfg["drive"]["oauth_token_file"] = str(_resolve(cfg["drive"]["oauth_token_file"]))

    # Resolve font paths.
    for section in ("top_caption", "bottom_caption"):
        cfg["compositor"][section]["font_path"] = str(_resolve(cfg["compositor"][section]["font_path"]))
        cfg["compositor"][section]["fallback_font_path"] = str(
            _resolve(cfg["compositor"][section]["fallback_font_path"])
        )
    cfg["compositor"]["watermark"]["font_path"] = str(_resolve(cfg["compositor"]["watermark"]["font_path"]))

    # Resolve local data/output paths and ensure directories exist.
    for key in ("local_memes_dir", "local_logs_dir"):
        resolved = _resolve(cfg["paths"][key])
        resolved.mkdir(parents=True, exist_ok=True)
        cfg["paths"][key] = str(resolved)
    for key in ("news_cache_file", "queue_file"):
        resolved = _resolve(cfg["paths"][key])
        resolved.parent.mkdir(parents=True, exist_ok=True)
        cfg["paths"][key] = str(resolved)

    cfg["reaction_index"]["csv_path"] = str(_resolve(cfg["reaction_index"]["csv_path"]))

    return cfg


DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"]


def get_drive_service(cfg: dict[str, Any], logger: logging.Logger):
    """Build an authenticated Google Drive v3 client, or None if no credentials
    are configured yet. Both reaction_picker.py and drive_uploader.py need the
    same auth, so it lives here rather than duplicated in each.

    The service account's client_email must be added as a Viewer/Editor on
    the target Drive folders - see README.md for setup steps.
    """
    sa_file = Path(cfg["drive"]["service_account_file"])
    if not sa_file.exists():
        logger.warning(
            f"No Drive service account file at {sa_file} - Drive calls will be skipped "
            "(pipeline falls back to offline/local behavior). See README.md to set up auth."
        )
        return None

    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    credentials = service_account.Credentials.from_service_account_file(str(sa_file), scopes=DRIVE_SCOPES)
    return build("drive", "v3", credentials=credentials, cache_discovery=False)


def get_logger(name: str, cfg: dict[str, Any] | None = None) -> logging.Logger:
    """Return a logger that writes to console + output/logs/pipeline.log."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # already configured (avoid duplicate handlers on reuse)

    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    logger.addHandler(console)

    if cfg is not None:
        log_dir = Path(cfg["paths"]["local_logs_dir"])
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_dir / "pipeline.log", encoding="utf-8")
        file_handler.setFormatter(fmt)
        logger.addHandler(file_handler)

    return logger
