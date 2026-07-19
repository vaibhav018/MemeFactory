"""Generate background images — DALL-E 3 or rich procedural gradient fallback."""
from __future__ import annotations

import io
import math
import os
import random
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFilter


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _procedural_bg(pillar: dict, w: int = 1080, h: int = 1080) -> Image.Image:
    """Create a visually rich background using geometric shapes and gradients."""
    palette = pillar.get("visual_palette", {})
    c1 = _hex_to_rgb(palette.get("primary", "#0D0D0D"))
    c2 = _hex_to_rgb(palette.get("gradient_to", "#1A1A1A"))
    accent = _hex_to_rgb(palette.get("accent", "#FFFFFF"))

    # Base diagonal gradient
    img = Image.new("RGB", (w, h))
    draw = ImageDraw.Draw(img)
    for y in range(h):
        for x in range(w):
            t = (x / w * 0.4 + y / h * 0.6)
            r = int(c1[0] + (c2[0] - c1[0]) * t)
            g = int(c1[1] + (c2[1] - c1[1]) * t)
            b = int(c1[2] + (c2[2] - c1[2]) * t)
            draw.point((x, y), fill=(r, g, b))

    # Large accent circle (top-right)
    cx, cy = int(w * 0.85), int(h * 0.15)
    r_size = int(w * 0.45)
    draw.ellipse([cx - r_size, cy - r_size, cx + r_size, cy + r_size],
                 fill=(*accent, 18))

    # Small accent circle (bottom-left)
    cx2, cy2 = int(w * 0.1), int(h * 0.88)
    r2 = int(w * 0.22)
    draw.ellipse([cx2 - r2, cy2 - r2, cx2 + r2, cy2 + r2],
                 fill=(*accent, 12))

    # Diagonal accent stripe
    stripe_w = int(w * 0.008)
    for offset in [int(w * 0.3), int(w * 0.55)]:
        pts = [(offset, 0), (offset + stripe_w, 0),
               (offset + stripe_w + h, h), (offset + h, h)]
        draw.polygon(pts, fill=(*accent, 25))

    # Subtle blur for depth
    img = img.filter(ImageFilter.GaussianBlur(radius=2))
    return img


def generate_background(
    dalle_prompt: str,
    pillar: dict,
    output_path: Path,
    size: int = 1080,
) -> Path:
    api_key = os.getenv("OPENAI_API_KEY")

    if api_key:
        try:
            resp = requests.post(
                "https://api.openai.com/v1/images/generations",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": "dall-e-3",
                    "prompt": dalle_prompt + " No text, no letters, no words.",
                    "n": 1,
                    "size": "1024x1024",
                    "quality": "hd",
                    "response_format": "url",
                },
                timeout=60,
            )
            resp.raise_for_status()
            img_url = resp.json()["data"][0]["url"]
            img_data = requests.get(img_url, timeout=30).content
            img = Image.open(io.BytesIO(img_data)).convert("RGB")
            img = img.resize((size, size), Image.LANCZOS)
            img.save(output_path, format="JPEG", quality=95)
            return output_path
        except Exception as exc:
            print(f"  [DALL-E fallback] {exc}")

    img = _procedural_bg(pillar, size, size)
    img.save(output_path, format="JPEG", quality=95)
    return output_path
