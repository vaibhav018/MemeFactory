"""Backward-compat shim.

The real logic moved to engine.visual.image_gen. This module keeps the
generate_background(prompt, pillar, output_path, size) signature so existing
pipeline.py imports and any other callers keep working.

Prefer importing engine.visual.image_gen.generate_image directly in new code.
"""
from __future__ import annotations

from pathlib import Path

from engine.visual.image_gen import generate_image


def generate_background(
    dalle_prompt: str,
    pillar: dict,
    output_path: Path,
    size: int = 1080,
) -> Path:
    return generate_image(dalle_prompt, pillar, output_path, size)
