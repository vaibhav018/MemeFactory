#!/usr/bin/env python3
"""Assemble a weekly roundup carousel: image cover, video items, image close.

Structurally what @evolving.ai runs — their 20-slide roundup carries nine video
children, each a news item over footage of that thing. This builds the same
shape at a smaller slide count.

    python scripts/build_roundup.py roundup.json

The input names the items and which clip belongs to each; the sweep
(scripts/discover_reels.py) is what finds the clips and their crops.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import requests

BASE = Path(__file__).resolve().parents[1]
REELS = BASE / "reels"
VIDEO_DIR = REELS / "public" / "video"


def load_env() -> None:
    env = BASE / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def fetch_clip(shortcode: str, dest: Path) -> None:
    if dest.exists():
        print(f"    have {dest.name}")
        return
    r = requests.post(
        "https://api.apify.com/v2/acts/apify~instagram-scraper/run-sync-get-dataset-items",
        params={"token": os.environ["APIFY_TOKEN"]}, timeout=300,
        json={"directUrls": [f"https://www.instagram.com/reel/{shortcode}/"],
              "resultsType": "details", "resultsLimit": 1, "addParentData": False})
    r.raise_for_status()
    url = r.json()[0].get("videoUrl")
    if not url:
        raise RuntimeError(f"{shortcode} has no videoUrl")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(requests.get(url, timeout=300).content)
    print(f"    fetched {dest.name} ({dest.stat().st_size // 1024} KB)")


def find_npx() -> str:
    """Resolve npx without trusting PATH.

    Node installs to a well-known directory on Windows but only lands on PATH
    for shells started after the install. A run that works in one terminal and
    dies in the next is this, every time.
    """
    import shutil
    for name in ("npx.cmd", "npx"):
        found = shutil.which(name)
        if found:
            return found
    for d in (Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "nodejs",
              Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "nodejs",
              Path(os.environ.get("APPDATA", "")) / "npm",
              Path("/usr/local/bin"), Path("/usr/bin")):
        for name in ("npx.cmd", "npx"):
            p = d / name
            if p.exists():
                return str(p)
    sys.exit("npx not found — install Node, or add it to PATH")


def render_news_slide(item: dict, out: Path) -> None:
    """Render one item through the NewsSlide composition."""
    props = REELS / "data" / f"_tmp_{out.stem}.news.json"
    props.write_text(json.dumps({
        "id": out.stem,
        "headline": item["headline"],
        "body": item["body"],
        "videoSrc": f"video/{item['clip']}.mp4",
        "sourceAspect": item.get("sourceAspect", 0.5625),
        "sourceCrop": item.get("sourceCrop"),
        "startFrom": item.get("startFrom", 0),
        "durationInSeconds": item.get("seconds", 8),
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    npx = find_npx()
    # npx.cmd shells out to `node` by bare name, so resolving npx is not enough
    # — its own directory has to be on PATH for the child process too.
    env = dict(os.environ)
    env["PATH"] = str(Path(npx).parent) + os.pathsep + env.get("PATH", "")

    cmd = [npx, "remotion", "render", "NewsSlide",
           str(out.resolve()), f"--props={props.resolve()}"]
    r = subprocess.run(cmd, cwd=REELS, capture_output=True, text=True, env=env)
    props.unlink(missing_ok=True)
    if r.returncode != 0 or not out.exists():
        raise RuntimeError(f"render failed: {r.stderr[-400:]}")
    print(f"    rendered {out.name} ({out.stat().st_size // 1024} KB)")


def normalise(spec: dict) -> list[dict]:
    """Accept either shape and return one ordered list of slides.

    The weekly roundup is cover + all-video + close, but a daily post mixes
    stills and video freely, so the general form is a single ordered `slides`
    list where each entry declares its own type.
    """
    if "slides" in spec:
        return spec["slides"]

    prompts = spec.get("image_prompts", [])
    out = [{"type": "still", "text": spec["hook"], "subline": spec["subline"],
            "prompt": prompts[0] if prompts else ""}]
    out += [{"type": "video", **it} for it in spec["items"]]
    out.append({"type": "still", "text": spec["close"], "subline": spec["close_sub"],
                "prompt": prompts[-1] if len(prompts) > 1 else ""})
    return out


def main() -> int:
    load_env()
    spec_path = Path(sys.argv[1] if len(sys.argv) > 1 else "roundup.json")
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    post_id = spec["id"]
    out_dir = BASE / "Generated_Memes" / post_id
    out_dir.mkdir(parents=True, exist_ok=True)

    sys.path.insert(0, str(BASE))
    from engine.visual.background_gen import generate_background
    from engine.visual.html_renderer import render_carousel

    slides = normalise(spec)
    order: list[Path] = []

    for n, sl in enumerate(slides, start=1):
        kind = sl.get("type", "video")
        label = sl.get("headline") or sl.get("text") or ""
        print(f"  [{n}] {kind:<5} {label[:58]}")

        if kind == "still":
            bg = out_dir / f"background_{n:02d}.jpg"
            if not bg.exists():
                generate_background(sl.get("prompt", ""), {}, bg)
            # Rendered one at a time: render_carousel picks a background by
            # slide position, so handing it the whole set would not map 1:1.
            made = render_carousel(
                [bg], [{"slide": 1, "text": sl["text"], "subline": sl.get("subline", "")}],
                {}, out_dir, f"{post_id}_s{n:02d}")
            order.append(made[0])
        else:
            clip = VIDEO_DIR / f"{sl['clip']}.mp4"
            if not clip.exists() and not sl.get("local"):
                fetch_clip(sl["clip"], clip)
            if not clip.exists():
                sys.exit(f"clip missing: {clip}")
            mp4 = out_dir / f"{post_id}_s{n:02d}.mp4"
            if not mp4.exists():
                render_news_slide(sl, mp4)
            order.append(mp4)

    manifest = out_dir / "carousel.json"
    manifest.write_text(json.dumps({
        "id": post_id,
        "caption": spec["caption"],
        "slides": [p.relative_to(BASE).as_posix() for p in order],
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    n_video = sum(1 for p in order if p.suffix == ".mp4")
    print(f"\n{len(order)} slides ({n_video} video) -> {manifest}")
    for p in order:
        print(f"  {p.suffix}  {p.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
