"""Free-first image generation with three-tier fallback.

Backends, in order:
  1. Cloudflare Workers AI  (FLUX-1 schnell) -- best quality, 320KB avg, 2-3s,
     10K images/day free. Needs CF_ACCOUNT_ID + CF_API_TOKEN in .env.
  2. Pollinations.ai        (FLUX-schnell) -- same model, ~24KB, no auth,
     rate-limited (~1 req / 15s), sometimes throttled.
  3. Procedural gradient    (existing pillar-palette fallback) -- always works.

The chain fires in order and returns as soon as one succeeds. A backend can
fail for network, HTTP, JSON, or content-filter reasons; every failure is
logged (so cron logs show which tier caught) and the next tier tries.

DALL-E is intentionally NOT wired here anymore -- the user asked for free-only.
Legacy env var OPENAI_API_KEY is ignored.
"""
from __future__ import annotations

import base64
import io
import math
import os
from pathlib import Path
from urllib.parse import quote

import requests
from PIL import Image, ImageDraw, ImageFilter

_CF_MODEL = "@cf/black-forest-labs/flux-1-schnell"
_HTTP_TIMEOUT = 90
_POLL_MODEL = "flux"


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


# ── backends ────────────────────────────────────────────────────────────────

def _cloudflare(prompt: str) -> bytes | None:
    """Return raw JPEG bytes from CF Workers AI, or None if unavailable/failed.

    CF's flux-1-schnell content filter is non-deterministic: the same prompt
    can return 400 then 200 on immediate retry. We try the original prompt,
    then one retry with a light rewrite (prepended safety wrapper) to nudge
    it past the filter.
    """
    acct = os.getenv("CF_ACCOUNT_ID")
    tok = os.getenv("CF_API_TOKEN")
    if not (acct and tok):
        print("  [image_gen] cloudflare skipped: CF_ACCOUNT_ID or CF_API_TOKEN not set")
        return None

    variants = [
        prompt,
        f"professional editorial illustration in a magazine style: {prompt}. cinematic composition.",
    ]
    url = f"https://api.cloudflare.com/client/v4/accounts/{acct}/ai/run/{_CF_MODEL}"
    headers = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}

    for attempt, p in enumerate(variants, 1):
        try:
            r = requests.post(url, headers=headers,
                              json={"prompt": p, "steps": 8},
                              timeout=_HTTP_TIMEOUT)
        except Exception as e:
            print(f"  [image_gen] cloudflare attempt {attempt} {type(e).__name__}: {e}")
            continue

        if r.status_code == 200:
            body = r.json()
            if body.get("success"):
                return base64.b64decode(body["result"]["image"])
            print(f"  [image_gen] cloudflare attempt {attempt} api-fail: {body.get('errors', body)}")
        else:
            print(f"  [image_gen] cloudflare attempt {attempt} HTTP {r.status_code}: {r.text[:140]}")
    return None


def _pollinations(prompt: str, size: int) -> bytes | None:
    """Return raw JPEG bytes from Pollinations.ai, or None if unavailable/failed."""
    try:
        url = (f"https://image.pollinations.ai/prompt/{quote(prompt)}"
               f"?width={size}&height={size}&model={_POLL_MODEL}"
               f"&nologo=true&enhance=true&safe=true")
        r = requests.get(url, timeout=_HTTP_TIMEOUT)
        if r.status_code != 200:
            print(f"  [image_gen] pollinations HTTP {r.status_code}")
            return None
        return r.content
    except Exception as e:
        print(f"  [image_gen] pollinations {type(e).__name__}: {e}")
        return None


def _procedural(pillar: dict, w: int, h: int) -> Image.Image:
    """Palette-driven gradient + accent shapes. Always works, always cheap."""
    palette = pillar.get("visual_palette", {})
    c1 = _hex_to_rgb(palette.get("primary", "#0D0D0D"))
    c2 = _hex_to_rgb(palette.get("gradient_to", "#1A1A1A"))
    accent = _hex_to_rgb(palette.get("accent", "#FFFFFF"))

    img = Image.new("RGB", (w, h))
    draw = ImageDraw.Draw(img)
    for y in range(h):
        for x in range(w):
            t = (x / w * 0.4 + y / h * 0.6)
            r = int(c1[0] + (c2[0] - c1[0]) * t)
            g = int(c1[1] + (c2[1] - c1[1]) * t)
            b = int(c1[2] + (c2[2] - c1[2]) * t)
            draw.point((x, y), fill=(r, g, b))

    cx, cy = int(w * 0.85), int(h * 0.15)
    r_size = int(w * 0.45)
    draw.ellipse([cx - r_size, cy - r_size, cx + r_size, cy + r_size], fill=(*accent, 18))

    cx2, cy2 = int(w * 0.1), int(h * 0.88)
    r2 = int(w * 0.22)
    draw.ellipse([cx2 - r2, cy2 - r2, cx2 + r2, cy2 + r2], fill=(*accent, 12))

    stripe_w = int(w * 0.008)
    for offset in [int(w * 0.3), int(w * 0.55)]:
        pts = [(offset, 0), (offset + stripe_w, 0),
               (offset + stripe_w + h, h), (offset + h, h)]
        draw.polygon(pts, fill=(*accent, 25))
    return img.filter(ImageFilter.GaussianBlur(radius=2))


# ── public API ──────────────────────────────────────────────────────────────

def generate_image(
    prompt: str,
    pillar: dict,
    output_path: Path,
    size: int = 1080,
) -> Path:
    """Try CF -> Pollinations -> procedural. Write the first success to output_path."""
    # Every backend gets a mild "no text, no letters" suffix -- FLUX likes to add
    # garbled text to backgrounds otherwise, which fights the compositor's own text.
    p = prompt + ". No text, no letters, no words, no watermark."

    for name, getter in (("cloudflare", lambda: _cloudflare(p)),
                         ("pollinations", lambda: _pollinations(p, size))):
        data = getter()
        if data is None:
            continue
        try:
            img = Image.open(io.BytesIO(data)).convert("RGB")
            if img.size != (size, size):
                img = img.resize((size, size), Image.LANCZOS)
            img.save(output_path, format="JPEG", quality=92)
            print(f"  [image_gen] used {name} ({len(data)//1024}KB)")
            return output_path
        except Exception as e:
            print(f"  [image_gen] {name} returned unopenable data: {e}")
            continue

    print(f"  [image_gen] all external backends failed, using procedural gradient")
    img = _procedural(pillar, size, size)
    img.save(output_path, format="JPEG", quality=92)
    return output_path
