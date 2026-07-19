"""Unified LLM client using raw HTTP — no SDK needed, only `requests`.

Supports Groq, Google Gemini, and OpenRouter. All have generous free tiers.

Provider selection (in priority order):
  1. LLM_PROVIDER env var  (groq | gemini | openrouter)
  2. config/settings.yaml  llm.provider field
  3. Auto-detect from which API key is present in .env

Usage:
    from engine.llm_client import complete
    text = complete(system="...", user="...", json_mode=True)
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import requests
import yaml

_CFG_PATH = Path(__file__).parent.parent / "config" / "settings.yaml"
_TIMEOUT = 90


def _load_provider_cfg() -> dict:
    try:
        with open(_CFG_PATH, encoding="utf-8") as f:
            return yaml.safe_load(f).get("llm", {})
    except Exception:
        return {}


def _pick_provider(cfg: dict) -> str:
    if p := os.getenv("LLM_PROVIDER"):
        return p.lower()
    if p := cfg.get("provider"):
        return p.lower()
    # auto-detect from keys present
    if os.getenv("GROQ_API_KEY"):
        return "groq"
    if os.getenv("GEMINI_API_KEY"):
        return "gemini"
    if os.getenv("OPENROUTER_API_KEY"):
        return "openrouter"
    sys.exit(
        "No LLM API key found. Add one of these to .env:\n"
        "  GROQ_API_KEY      — free at console.groq.com\n"
        "  GEMINI_API_KEY    — free at aistudio.google.com\n"
        "  OPENROUTER_API_KEY— free at openrouter.ai"
    )


def _groq(system: str, user: str, model: str, json_mode: bool) -> str:
    key = os.getenv("GROQ_API_KEY")
    if not key:
        sys.exit("GROQ_API_KEY not set")
    payload: dict = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.85,
        "max_tokens": 2048,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    resp = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json=payload,
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def _gemini(system: str, user: str, model: str, json_mode: bool) -> str:
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        sys.exit("GEMINI_API_KEY not set")
    payload: dict = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"parts": [{"text": user}]}],
        "generationConfig": {
            "temperature": 0.85,
            "maxOutputTokens": 2048,
        },
    }
    if json_mode:
        payload["generationConfig"]["responseMimeType"] = "application/json"
    resp = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}",
        json=payload,
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    parts = resp.json()["candidates"][0]["content"]["parts"]
    return "".join(p["text"] for p in parts)


def _openrouter(system: str, user: str, model: str, json_mode: bool) -> str:
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        sys.exit("OPENROUTER_API_KEY not set")
    payload: dict = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.85,
        "max_tokens": 2048,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    resp = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/vaibhav018/MemeFactory",
        },
        json=payload,
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def complete(system: str, user: str, json_mode: bool = False) -> str:
    """Call the configured LLM. Returns the response text."""
    cfg = _load_provider_cfg()
    provider = _pick_provider(cfg)

    if provider == "groq":
        model = cfg.get("groq_model", "llama-3.3-70b-versatile")
        return _groq(system, user, model, json_mode)
    elif provider == "gemini":
        model = cfg.get("gemini_model", "gemini-2.0-flash")
        return _gemini(system, user, model, json_mode)
    elif provider == "openrouter":
        model = cfg.get("openrouter_model", "meta-llama/llama-3.3-70b-instruct:free")
        return _openrouter(system, user, model, json_mode)
    else:
        sys.exit(f"Unknown LLM provider: '{provider}'. Use groq, gemini, or openrouter.")


def complete_json(system: str, user: str) -> dict | list:
    """Call LLM in JSON mode and parse the result."""
    raw = complete(system, user, json_mode=True)
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())
