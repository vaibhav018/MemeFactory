#!/usr/bin/env python3
"""Record a web page as footage for a NewsSlide.

Half our items are tools and repos, and for those the footage is a screen
recording we make ourselves — a repo page, a star graph, a tool's UI. That
sidesteps the expensive half of the roundup format: no sourcing, no crediting
someone else's clip, and the footage is exactly on-topic every time.

    python scripts/record_screen.py github vercel/next.js --out repo.mp4
    python scripts/record_screen.py stars  vercel/next.js --out stars.mp4
    python scripts/record_screen.py page   https://example.com --out page.mp4

Output is a 1440x810 (16:9) mp4 with no cursor and no browser chrome, which
NewsSlide crops and rounds like any other clip.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = Path(__file__).resolve().parents[1]
W, H = 1440, 810

# A repo page is mostly chrome. Hide the parts that date the clip or pull the
# eye away from the numbers we are pointing at.
HIDE_CSS = """
  .js-header-wrapper, .header-logged-out, header.Header,
  .js-notice, .flash-notice, .js-cookie-consent, dialog,
  .footer, footer, .js-feature-preview-indicator { display: none !important; }
  html { scroll-behavior: auto !important; }
  *, *::before, *::after { animation-play-state: paused !important; }
"""


def _encode_cmd() -> tuple[list[str], Path | None]:
    """Return an ffmpeg command head, and the cwd it must run from.

    Playwright ships an ffmpeg, but it is a stripped build with no libx264 —
    it can capture the webm and then not transcode it. Remotion's copy is a
    full build, and `npx remotion ffmpeg` resolves it against the nearest
    node_modules, which means running from reels/.
    """
    found = shutil.which("ffmpeg")
    if found:
        return [found], None

    import os
    for name in ("npx.cmd", "npx"):
        npx = shutil.which(name)
        if npx:
            return [npx, "remotion", "ffmpeg"], BASE / "reels"
    nodedir = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "nodejs"
    for name in ("npx.cmd", "npx"):
        if (nodedir / name).exists():
            return [str(nodedir / name), "remotion", "ffmpeg"], BASE / "reels"
    sys.exit("no ffmpeg and no npx to reach Remotion's copy")


def _smooth_scroll(page, total_px: int, seconds: float) -> None:
    """Scroll by small steps so the recording reads as motion, not as jumps."""
    steps = max(1, int(seconds * 30))
    page.evaluate(
        """([total, steps]) => new Promise(res => {
             let i = 0;
             const tick = () => {
               window.scrollBy(0, total / steps);
               if (++i >= steps) return res();
               requestAnimationFrame(tick);
             };
             tick();
           })""",
        [total_px, steps],
    )


def record(mode: str, target: str, out: Path, seconds: float) -> None:
    tmp = out.parent / "_rec"
    tmp.mkdir(parents=True, exist_ok=True)

    if mode == "github":
        url = f"https://github.com/{target}"
    elif mode == "stars":
        url = f"https://star-history.com/#{target}&Date"
    else:
        url = target

    with sync_playwright() as pw:
        browser = pw.chromium.launch(args=["--hide-scrollbars", "--force-device-scale-factor=1"])
        ctx = browser.new_context(
            viewport={"width": W, "height": H},
            device_scale_factor=1,
            record_video_dir=str(tmp),
            record_video_size={"width": W, "height": H},
            color_scheme="dark",
        )
        page = ctx.new_page()
        print(f"  loading {url}")
        page.goto(url, wait_until="domcontentloaded", timeout=90_000)
        page.add_style_tag(content=HIDE_CSS)

        if mode == "stars":
            # The chart animates in and is the whole point; give it time to draw
            # rather than scrolling past a half-rendered canvas.
            page.wait_for_timeout(6_000)
            page.wait_for_timeout(int(seconds * 1000))
        else:
            page.wait_for_timeout(2_500)
            _smooth_scroll(page, 1400, seconds * 0.75)
            page.wait_for_timeout(1_200)

        ctx.close()
        browser.close()

    webm = max(tmp.glob("*.webm"), key=lambda p: p.stat().st_mtime)
    head, cwd = _encode_cmd()
    out.parent.mkdir(parents=True, exist_ok=True)
    # Absolute paths: cwd may be reels/ for the npx route.
    import os
    env = dict(os.environ)
    env["PATH"] = str(Path(head[0]).parent) + os.pathsep + env.get("PATH", "")
    r = subprocess.run(
        head + ["-y", "-i", str(webm.resolve()), "-c:v", "libx264",
                "-pix_fmt", "yuv420p", "-preset", "medium", "-crf", "22",
                "-an", str(out.resolve())],
        cwd=cwd, capture_output=True, text=True, env=env,
    )
    if r.returncode != 0 or not out.exists():
        sys.exit(f"transcode failed:\n{r.stderr[-600:]}")
    for f in tmp.glob("*"):
        f.unlink()
    tmp.rmdir()
    print(f"  {out.name} ({out.stat().st_size // 1024} KB)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["github", "stars", "page"])
    ap.add_argument("target")
    ap.add_argument("--out", required=True)
    ap.add_argument("--seconds", type=float, default=8.0)
    a = ap.parse_args()
    record(a.mode, a.target, Path(a.out), a.seconds)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
