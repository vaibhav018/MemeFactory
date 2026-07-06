#!/usr/bin/env python3
"""Publish the most recently generated meme to Instagram.

Reads data/last_meme.json (written by auto_meme.py after it renders a meme)
for the image's repo-relative path + caption, builds the public
raw.githubusercontent.com URL for it, and publishes via the Instagram Graph
API using the Instagram Login flow (graph.instagram.com - no linked Facebook
Page required).

IMPORTANT: the image must already be pushed to `main` before this runs, since
Instagram fetches it from the public raw URL rather than accepting an upload.
In the GitHub Actions workflow this step runs after the "git push" step.

Env vars required (GitHub Actions repo secrets locally via .env):
  IG_ACCESS_TOKEN  - Instagram access token (Instagram Login flow)
  IG_USER_ID       - numeric Instagram account id (from graph.instagram.com/me)

GITHUB_REPOSITORY ("owner/repo") is auto-provided by GitHub Actions; falls
back to DEFAULT_REPO for local runs.

Usage:
  python instagram_publisher.py             # publish data/last_meme.json
  python instagram_publisher.py --dry-run   # print what would happen, no API calls
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

BASE = Path(__file__).resolve().parent
STATE_FILE = BASE / "data" / "last_meme.json"
GRAPH = "https://graph.instagram.com/v21.0"
DEFAULT_REPO = "vaibhav018/MemeFactory"


def publish(image_url: str, caption: str, token: str, ig_user_id: str) -> None:
    resp = requests.post(
        f"{GRAPH}/{ig_user_id}/media",
        data={"image_url": image_url, "caption": caption, "access_token": token},
        timeout=30,
    )
    resp.raise_for_status()
    creation_id = resp.json()["id"]
    print(f">> Created media container: {creation_id}")

    for _ in range(10):
        status = requests.get(
            f"{GRAPH}/{creation_id}",
            params={"fields": "status_code", "access_token": token},
            timeout=15,
        ).json().get("status_code")
        if status == "FINISHED":
            break
        if status == "ERROR":
            sys.exit("!! Media container failed processing on Instagram's side")
        time.sleep(3)

    publish_resp = requests.post(
        f"{GRAPH}/{ig_user_id}/media_publish",
        data={"creation_id": creation_id, "access_token": token},
        timeout=30,
    )
    publish_resp.raise_for_status()
    print(f">> Published: {publish_resp.json()}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish the latest generated meme to Instagram")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be posted, no API calls")
    args = parser.parse_args()

    if not STATE_FILE.exists():
        sys.exit(f"!! {STATE_FILE} not found - run auto_meme.py first")
    state = json.loads(STATE_FILE.read_text(encoding="utf-8"))

    repo = os.environ.get("GITHUB_REPOSITORY", DEFAULT_REPO)
    image_url = f"https://raw.githubusercontent.com/{repo}/main/{state['path']}"
    caption = state.get("caption", "")

    print(f">> Image URL: {image_url}")
    print(f">> Caption: {caption}")

    if args.dry_run:
        print("[dry-run] Skipping API calls.")
        return

    token = os.environ.get("IG_ACCESS_TOKEN")
    ig_user_id = os.environ.get("IG_USER_ID")
    if not token or not ig_user_id:
        sys.exit("!! IG_ACCESS_TOKEN / IG_USER_ID not set")

    publish(image_url, caption, token, ig_user_id)


if __name__ == "__main__":
    main()
