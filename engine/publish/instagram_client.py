"""Instagram Graph API client with carousel support.

For carousels:
  1. Create a media container for each slide (is_carousel_item=true)
  2. Create a CAROUSEL container with children IDs
  3. Poll status until FINISHED
  4. Publish

Images must be publicly accessible URLs (pushed to GitHub raw first).
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from urllib.parse import quote

import requests

GRAPH = "https://graph.instagram.com/v21.0"
DEFAULT_REPO = "vaibhav018/MemeFactory"


def _token() -> str:
    t = os.getenv("IG_ACCESS_TOKEN")
    if not t:
        sys.exit("IG_ACCESS_TOKEN not set")
    return t


def _user_id() -> str:
    u = os.getenv("IG_USER_ID")
    if not u:
        sys.exit("IG_USER_ID not set")
    return u


def _raw_url(repo_path: str, repo: str = "") -> str:
    repo = repo or os.getenv("GITHUB_REPOSITORY", DEFAULT_REPO)
    encoded = quote(repo_path, safe="/")
    return f"https://raw.githubusercontent.com/{repo}/main/{encoded}"


def _wait_for_container(container_id: str, timeout: int = 120) -> None:
    token = _token()
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = requests.get(
            f"{GRAPH}/{container_id}",
            params={"fields": "status_code", "access_token": token},
            timeout=15,
        ).json()
        status = resp.get("status_code")
        if status == "FINISHED":
            return
        if status == "ERROR":
            raise RuntimeError(f"Instagram media container {container_id} failed: {resp}")
        time.sleep(4)
    raise TimeoutError(f"Container {container_id} not ready after {timeout}s")


def publish_single(image_repo_path: str, caption: str, dry_run: bool = False) -> str:
    """Publish a single image. Returns media ID or '[dry-run]'."""
    url = _raw_url(image_repo_path)
    print(f"  image_url: {url}")
    if dry_run:
        print("  [dry-run] skipping publish")
        return "[dry-run]"

    token, uid = _token(), _user_id()
    r = requests.post(f"{GRAPH}/{uid}/media",
                      data={"image_url": url, "caption": caption, "access_token": token},
                      timeout=30)
    r.raise_for_status()
    cid = r.json()["id"]
    _wait_for_container(cid)

    pub = requests.post(f"{GRAPH}/{uid}/media_publish",
                        data={"creation_id": cid, "access_token": token},
                        timeout=30)
    pub.raise_for_status()
    media_id = pub.json()["id"]
    print(f"  Published single post: {media_id}")
    return media_id


def publish_reel(video_repo_path: str, caption: str, dry_run: bool = False,
                 share_to_feed: bool = True, cover_repo_path: str = "") -> str:
    """Publish a Reel. Returns media ID or '[dry-run]'.

    Reels differ from images in two ways that matter operationally:

    1. Instagram transcodes the video server-side, so the container takes far
       longer to reach FINISHED than an image does — minutes, not seconds.
       Hence the longer timeout rather than the default 120s.
    2. The MP4 must be reachable at a public URL when Instagram fetches it,
       which means the render has to be committed and pushed *before* this
       runs. A container created against an unpushed path fails with a
       generic ERROR that tells you nothing.
    """
    url = _raw_url(video_repo_path)
    print(f"  video_url: {url}")
    if dry_run:
        print("  [dry-run] skipping publish")
        return "[dry-run]"

    token, uid = _token(), _user_id()
    payload = {
        "media_type": "REELS",
        "video_url": url,
        "caption": caption,
        "share_to_feed": "true" if share_to_feed else "false",
        "access_token": token,
    }
    if cover_repo_path:
        # Without this Instagram picks its own frame, which is often a
        # mid-transition one with half a caption on screen.
        payload["thumb_offset"] = "0"
        payload["cover_url"] = _raw_url(cover_repo_path)

    r = requests.post(f"{GRAPH}/{uid}/media", data=payload, timeout=60)
    if not r.ok:
        raise RuntimeError(f"Reel container creation failed: {r.status_code} {r.text[:300]}")
    cid = r.json()["id"]
    print(f"  container {cid} created; waiting for transcode")

    _wait_for_container(cid, timeout=600)

    pub = requests.post(f"{GRAPH}/{uid}/media_publish",
                        data={"creation_id": cid, "access_token": token},
                        timeout=60)
    pub.raise_for_status()
    media_id = pub.json()["id"]
    print(f"  Published reel: {media_id}")
    return media_id


def publish_carousel(image_repo_paths: list[str], caption: str, dry_run: bool = False) -> str:
    """Publish a carousel of images. Returns carousel media ID."""
    if len(image_repo_paths) < 2:
        raise ValueError("Carousel requires at least 2 images")

    print(f"  Publishing carousel: {len(image_repo_paths)} slides")
    if dry_run:
        for p in image_repo_paths:
            print(f"  [dry-run] slide: {_raw_url(p)}")
        return "[dry-run]"

    token, uid = _token(), _user_id()

    # Step 1: create child containers.
    #
    # A carousel may mix images and videos, which is what competitors use to
    # break up an otherwise static swipe. The extension decides the child type;
    # a video child also has to finish transcoding before the parent container
    # will accept it, so those are waited on individually.
    child_ids = []
    for path in image_repo_paths:
        url = _raw_url(path)
        is_video = path.lower().endswith((".mp4", ".mov"))
        payload = {"is_carousel_item": "true", "access_token": token}
        if is_video:
            payload |= {"media_type": "VIDEO", "video_url": url}
        else:
            payload["image_url"] = url

        r = requests.post(f"{GRAPH}/{uid}/media", data=payload, timeout=60)
        if not r.ok:
            raise RuntimeError(
                f"carousel child failed ({'video' if is_video else 'image'}) "
                f"{url}: {r.status_code} {r.text[:250]}")
        cid = r.json()["id"]
        if is_video:
            print(f"    video child {cid} — waiting for transcode")
            _wait_for_container(cid, timeout=600)
        child_ids.append(cid)

    # Step 2: create carousel container
    r = requests.post(
        f"{GRAPH}/{uid}/media",
        data={
            "media_type": "CAROUSEL",
            "children": ",".join(child_ids),
            "caption": caption,
            "access_token": token,
        },
        timeout=30,
    )
    r.raise_for_status()
    carousel_cid = r.json()["id"]
    _wait_for_container(carousel_cid)

    # Step 3: publish — retry on transient app-rate-limit (code 4 / subcode 2207051)
    for attempt in range(1, 5):
        pub = requests.post(
            f"{GRAPH}/{uid}/media_publish",
            data={"creation_id": carousel_cid, "access_token": token},
            timeout=30,
        )
        if pub.ok:
            media_id = pub.json()["id"]
            print(f"  Published carousel: {media_id}")
            return media_id

        err = pub.json().get("error", {})
        code = err.get("code")
        subcode = err.get("error_subcode")

        # Transient Instagram errors — back off and retry
        transient = (
            (code == 4 and subcode == 2207051) or   # app rate limit
            (code == -1 and subcode == 2207085)      # generic internal error
        )
        if transient:
            wait = 90 * attempt  # 90s, 180s, 270s
            print(f"  Instagram transient error ({code}/{subcode}) — waiting {wait}s (retry {attempt}/4)...")
            time.sleep(wait)
            continue

        # Any other error: fail immediately with details
        raise RuntimeError(f"Instagram publish failed ({pub.status_code}): {pub.json()}")

    raise RuntimeError("Instagram publish failed after 4 retries — rate limit persisting")
