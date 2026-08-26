"""Render carousel slides by screenshotting an HTML template with Chromium.

Why this exists
---------------
`carousel_compositor.py` draws text over a generated photo with Pillow. That
architecture caps quality: the image model cannot know where the text will
land, so every background has to be busy-but-neutral, and Pillow gives us
rectangles and a font file with no grid or real typography.

This module renders `templates/slide.html` in headless Chromium and
screenshots it at 1080x1350 (4:5). Full CSS, real web typography, deterministic
output, no image API on the critical path. Backgrounds become an *optional*
texture layer behind a controlled type layer.

Drop-in: `render_carousel()` matches `compose_carousel()`'s signature, so
pipeline.py can switch between them behind a config flag.

Requires: playwright + `python -m playwright install chromium`.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

_BASE = Path(__file__).resolve().parents[2]
_TEMPLATE = _BASE / "templates" / "slide.html"
_W, _H = 1080, 1350          # Instagram 4:5 portrait


class RendererUnavailable(RuntimeError):
    """Playwright or its Chromium build is missing. Caller should fall back."""


def _check() -> None:
    try:
        import playwright  # noqa: F401
    except ImportError as e:  # pragma: no cover - environment dependent
        raise RendererUnavailable(
            "playwright not installed — pip install playwright && "
            "python -m playwright install chromium"
        ) from e
    if not _TEMPLATE.exists():
        raise RendererUnavailable(f"template missing: {_TEMPLATE}")


def render_carousel(
    bg_paths,
    slides: list[dict],
    pillar: dict,
    output_dir: Path,
    post_id: str,
    handle: str = "@profit_prompts_",
    use_texture: bool = False,
) -> list[Path]:
    """Render every slide to JPEG. Returns the list of written paths.

    Mirrors compose_carousel().

    bg_paths[0] is the COVER and always fills slide 1's photo panel — that is
    the whole point of the assets/curated/<id>/cover.jpg convention. If a
    second image is supplied it backs the closing CTA so the carousel
    bookends. Interior slides are typographic and take an image only when
    use_texture is True.
    """
    _check()
    from playwright.sync_api import sync_playwright

    if isinstance(bg_paths, (str, Path)):
        bg_paths = [Path(bg_paths)]
    else:
        bg_paths = [Path(p) for p in (bg_paths or [])]

    output_dir.mkdir(parents=True, exist_ok=True)
    total = len(slides)
    written: list[Path] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--font-render-hinting=none"])
        page = browser.new_page(
            viewport={"width": _W, "height": _H},
            device_scale_factor=1,
        )
        try:
            for i, slide in enumerate(slides, start=1):
                payload = {
                    "slide": i,
                    "total": total,
                    "handle": handle,
                    "data": slide,
                    "bg": None,
                }
                # Background assignment by position, not rotation:
                #   [cover]                  -> slide 1 only
                #   [cover, last]            -> slide 1 and the closing slide
                #   [cover, texture, last]   -> plus one shared texture behind
                #                               every interior slide
                #
                # The interior texture is deliberately ONE image rather than
                # five. Five unrelated generations behind five slides fight
                # each other; a single atmospheric field from the same world as
                # the cover makes the deck read as one piece.
                chosen = None
                if bg_paths:
                    if i == 1:
                        chosen = bg_paths[0]
                    elif i == total and len(bg_paths) >= 2:
                        chosen = bg_paths[-1]
                    elif len(bg_paths) >= 3:
                        chosen = bg_paths[1]
                    elif use_texture:
                        chosen = bg_paths[(i - 1) % len(bg_paths)]
                if chosen is not None and chosen.exists():
                    payload["bg"] = chosen.resolve().as_uri()

                # Inject before any of the template's own script runs.
                page.add_init_script(f"window.SLIDE = {json.dumps(payload)};")
                page.goto(_TEMPLATE.resolve().as_uri())
                page.wait_for_load_state("networkidle")
                # The template runs its autofit only after webfonts resolve,
                # then stamps data-ready. Shooting earlier catches type that
                # was measured against fallback metrics.
                page.wait_for_function(
                    "document.documentElement.dataset.ready === '1'", timeout=15000
                )

                out = output_dir / f"{post_id}_slide_{i:02d}.jpg"
                page.locator("#slide").screenshot(
                    path=str(out), type="jpeg", quality=94
                )
                written.append(out)
                print(f"    slide {i}/{total} ✓ (html)")
        finally:
            browser.close()

    return written


def render_slide_video(
    slide: dict,
    output_path: Path,
    slide_num: int,
    total_slides: int,
    bg: Path | None = None,
    handle: str = "@profit_prompts_",
    seconds: float = 6.0,
    fps: int = 24,
) -> Path:
    """Render one slide as a short MP4 for use as a carousel video child.

    Instagram carousels accept video children, and competitors use one to break
    up an otherwise static swipe. Rather than rebuild the slide design in
    Remotion, this drives the same templates/slide.html through a progress
    parameter and captures frames — one design, two output formats.

    Frames are captured by calling setProgress() rather than reloading, so the
    page lays out and loads fonts once. Encoding uses Remotion's bundled ffmpeg
    (image2 demuxer, libx264), which is already a dependency.
    """
    _check()
    from playwright.sync_api import sync_playwright

    frames_dir = output_path.parent / f".frames_{output_path.stem}"
    if frames_dir.exists():
        shutil.rmtree(frames_dir)
    frames_dir.mkdir(parents=True, exist_ok=True)

    n = max(2, int(round(seconds * fps)))
    payload = {
        "slide": slide_num,
        "total": total_slides,
        "handle": handle,
        "data": slide,
        "bg": bg.resolve().as_uri() if bg and bg.exists() else None,
        "progress": 0.0,
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--font-render-hinting=none"])
        page = browser.new_page(viewport={"width": _W, "height": _H},
                                device_scale_factor=1)
        try:
            page.add_init_script(f"window.SLIDE = {json.dumps(payload)};")
            page.goto(_TEMPLATE.resolve().as_uri())
            page.wait_for_load_state("networkidle")
            page.wait_for_function(
                "document.documentElement.dataset.ready === '1'", timeout=15000)

            shot = page.locator("#slide")
            for i in range(n):
                page.evaluate("p => window.setProgress(p)", i / (n - 1))
                shot.screenshot(path=str(frames_dir / f"f_{i:05d}.png"))
        finally:
            browser.close()

    _encode(frames_dir, output_path, fps)
    shutil.rmtree(frames_dir, ignore_errors=True)
    print(f"    video slide {slide_num} ✓ ({seconds:g}s, {output_path.stat().st_size // 1024} KB)")
    return output_path


def _encode(frames_dir: Path, output_path: Path, fps: int) -> None:
    """Encode a frame sequence to H.264. Instagram re-encodes anyway, so this
    targets compatibility over bitrate: yuv420p and an even pixel size are the
    two things it actually rejects."""
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        cmd_head, cwd = [ffmpeg], _BASE
    else:
        npx = shutil.which("npx.cmd") or shutil.which("npx")
        if not npx:
            raise RendererUnavailable("no ffmpeg on PATH and no npx to reach Remotion's copy")
        # `npx remotion` resolves against the nearest node_modules, which lives
        # in reels/ — running it from the repo root fails with "could not
        # determine executable to run".
        cmd_head, cwd = [npx, "remotion", "ffmpeg"], _BASE / "reels"

    # Absolute paths: cwd may be reels/ for the npx route, so anything relative
    # would resolve against the wrong directory.
    cmd = cmd_head + [
        "-y", "-loglevel", "error",
        "-framerate", str(fps),
        "-i", str((frames_dir / "f_%05d.png").resolve()),
        "-c:v", "libx264", "-preset", "medium", "-crf", "22",
        "-pix_fmt", "yuv420p",
        str(output_path.resolve()),
    ]
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0 or not output_path.exists():
        raise RuntimeError(f"ffmpeg failed ({r.returncode}): {r.stderr[-400:]}")


def selftest(output_dir: Path | None = None) -> list[Path]:
    """Render one slide of every layout so the template can be eyeballed."""
    out = output_dir or (_BASE / "output" / "template_selftest")
    demo = [
        {"text": "5 prompts that make any AI stop writing like a robot",
         "kicker": "AI TOOLS"},
        {"text": "Everyone can smell AI writing now. The tell is not the model "
                 "— it is the five defaults every model ships with."},
        {"layout": "step", "step_num": "1", "title": "Ban the connectors",
         "body": "Paste this: rewrite without delve, moreover, furthermore, in "
                 "conclusion. Those words carry most of the AI smell."},
        {"layout": "big_stat", "stat": "83", "unit": "% ",
         "caption": "of readers say they can spot AI copy in one paragraph"},
        {"layout": "split",
         "left_label": "DEFAULT", "left_text": "Every sentence lands at 15 to 20 words.",
         "right_label": "FIXED", "right_text": "One under five words. One over twenty-five."},
        {"layout": "numbered", "items": [
            {"num": "01", "title": "Ban connectors", "desc": "Kill the seven tell-tale words"},
            {"num": "02", "title": "Vary rhythm", "desc": "Mix sentence lengths hard"},
            {"num": "03", "title": "Name a reader", "desc": "One skeptical person, not an audience"},
            {"num": "04", "title": "Cut the wrap-up", "desc": "End on the last real point"},
            {"num": "05", "title": "Take a side", "desc": "Remove every hedge word"},
        ]},
        {"text": "Save this before your next draft"},
    ]
    return render_carousel([], demo, {}, out, "selftest")


if __name__ == "__main__":
    paths = selftest()
    print(f"\nWrote {len(paths)} slides to {paths[0].parent}")
