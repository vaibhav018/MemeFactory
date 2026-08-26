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
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = Path(__file__).resolve().parents[1]

# 4:3, not 16:9. The slide is 4:5, so a wide clip lands as a short letterbox
# with the page text scaled to ~0.67 and unreadable on a phone. A squarer
# capture fills the window, which means bigger type at the same slide size.
W, H = 1200, 900

# GitHub's body text is ~14px. Zooming the page before capture is what makes
# it legible after the clip is scaled into the slide.
ZOOM = 1.2

# A repo page is mostly chrome. Hide the parts that date the clip or pull the
# eye away from the numbers we are pointing at.
HIDE_CSS = """
  /* GitHub serves a different header to logged-out visitors, so hiding one
     class is not enough — the marketing nav (Platform/Solutions/Pricing plus
     Sign in) rides on .HeaderMenu and .AppHeader. */
  header, .AppHeader, .HeaderMenu, .js-header-wrapper, .header-logged-out,
  .js-notice, .flash, .flash-notice, .js-cookie-consent, dialog,
  .footer, footer, .js-feature-preview-indicator,
  [data-testid="cookie-consent"], .position-fixed.bottom-0
    { display: none !important; }
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


def record(mode: str, target: str, out: Path, seconds: float,
           scroll_px: int = 620) -> None:
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
        # Injected before any page script runs, and re-asserted on mutation, so
        # the chrome is never visible — not even in the opening frames. Adding
        # the style after load left GitHub's marketing nav on screen until
        # hydration finished, which is the first second of every clip.
        page.add_init_script(
            """(() => {
                 const css = %s;
                 const put = () => {
                   if (!document.head) return;
                   if (document.getElementById('__hide')) return;
                   const s = document.createElement('style');
                   s.id = '__hide';
                   s.textContent = css;
                   document.head.appendChild(s);
                 };
                 put();
                 document.addEventListener('DOMContentLoaded', put);
                 new MutationObserver(put).observe(document.documentElement,
                   {childList: true, subtree: true});
               })()""" % json.dumps(HIDE_CSS)
        )
        print(f"  loading {url}")
        page.goto(url, wait_until="domcontentloaded", timeout=90_000)
        # SPAs (star-history among them) redirect straight after load, which
        # destroys the execution context mid-call. Settle first, and treat the
        # style tag as best-effort — it is cosmetic, not the recording.
        try:
            page.wait_for_load_state("networkidle", timeout=20_000)
        except Exception:
            pass
        try:
            page.add_style_tag(content=HIDE_CSS)
            if mode != "stars":
                page.evaluate(f"document.body.style.zoom = '{ZOOM}'")
        except Exception:
            print("  (style tag skipped — page navigated)")

        if mode == "stars":
            # The chart animates in and is the whole point; give it time to draw
            # rather than scrolling past a half-rendered canvas.
            page.wait_for_timeout(6_000)
            page.wait_for_timeout(int(seconds * 1000))
        else:
            # Linger on the top of the page. The star count, licence and
            # description are the reason the clip exists; scrolling deep into
            # the README loses all three within a couple of seconds.
            page.wait_for_timeout(3_000)
            # GitHub hydrates and re-renders its header after the first style
            # tag lands, putting the marketing nav back. Re-apply once settled.
            try:
                page.add_style_tag(content=HIDE_CSS)
            except Exception:
                pass
            _smooth_scroll(page, scroll_px, seconds * 0.6)
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

    # Always leave a frame to look at. A capture can succeed and still be
    # worthless — star-history now serves a "add a GitHub token" modal instead
    # of a chart, and the recording of that modal transcoded perfectly.
    try:
        import cv2
        cap = cv2.VideoCapture(str(out))
        n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(n * 0.75))
        ok, fr = cap.read()
        if ok:
            shot = out.with_suffix(".frame.jpg")
            cv2.imwrite(str(shot), fr)
            print(f"  check the frame: {shot}")
        cap.release()
    except Exception:
        pass
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
    ap.add_argument("--scroll", type=int, default=620,
                    help="pixels to travel; keep it small to stay near the top")
    a = ap.parse_args()
    record(a.mode, a.target, Path(a.out), a.seconds, a.scroll)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
