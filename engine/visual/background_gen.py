"""Generate background images via DALL-E 3 or fall back to gradient.

DALL-E 3 is called when OPENAI_API_KEY is set. Otherwise a solid gradient
is rendered using Pillow — this keeps the pipeline running without an
OpenAI key and during API outages.
"""
from __future__ import annotations

import io
import os
import struct
import zlib
from pathlib import Path

import requests
from PIL import Image, ImageDraw


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _gradient_image(color_top: str, color_bottom: str, w: int = 1080, h: int = 1080) -> Image.Image:
    img = Image.new("RGB", (w, h))
    draw = ImageDraw.Draw(img)
    r1, g1, b1 = _hex_to_rgb(color_top)
    r2, g2, b2 = _hex_to_rgb(color_bottom)
    for y in range(h):
        t = y / h
        r = int(r1 + (r2 - r1) * t)
        g = int(g1 + (g2 - g1) * t)
        b = int(b1 + (b2 - b1) * t)
        draw.line([(0, y), (w, y)], fill=(r, g, b))
    return img


def generate_background(
    dalle_prompt: str,
    pillar: dict,
    output_path: Path,
    size: int = 1080,
) -> Path:
    """Generate background and save to output_path. Returns the path."""
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

    palette = pillar.get("visual_palette", {})
    img = _gradient_image(
        palette.get("primary", "#0D0D0D"),
        palette.get("gradient_to", "#1A1A1A"),
        size, size,
    )
    img.save(output_path, format="JPEG", quality=95)
    return output_path
