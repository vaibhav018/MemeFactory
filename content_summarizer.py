"""Fetches the real article text for a headline (via its direct outlet RSS
link) and condenses it into a short caption using a free, local, open-source
summarization model - no paid API, no per-request billing.

Requires headlines sourced from direct outlet RSS feeds (Sakshi, 123telugu,
TV9 Telugu, ...), not Google News search RSS - Google's RSS links are
client-side JS redirects to the Google News interstitial page, not real HTTP
redirects, so there is no article body to fetch through them at all.

Every failure mode (site blocks scraping, article too short, model error)
returns None so the caller falls back to the bare headline, same as before
this feature existed.
"""
from __future__ import annotations

import trafilatura

# distilbart-cnn-12-6 is trained purely on English news (CNN/DailyMail) - fed
# Telugu-script text it doesn't produce a bad *translation* of a summary, it
# produces outright punctuation-only garbage (verified empirically). Since a
# large share of headlines are now Telugu-native (Sakshi is 100% Telugu,
# TV9/123telugu are mixed), articles must be checked for script before
# summarizing - otherwise garbage captions would go out regularly.
_TELUGU_BLOCK = range(0x0C00, 0x0C7F + 1)


def _is_mostly_telugu(text: str, threshold: float = 0.15) -> bool:
    letters = [ch for ch in text if ch.isalpha()]
    if not letters:
        return False
    telugu = sum(1 for ch in letters if ord(ch) in _TELUGU_BLOCK)
    return (telugu / len(letters)) > threshold


_MODEL_NAME = "sshleifer/distilbart-cnn-12-6"
_tokenizer = None
_model = None


def _get_model():
    """Loads the tokenizer/model directly via AutoModelForSeq2SeqLM instead of
    the high-level pipeline("summarization", ...) helper, which the installed
    transformers version no longer supports as a task name."""
    global _tokenizer, _model
    if _model is None:
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        _tokenizer = AutoTokenizer.from_pretrained(_MODEL_NAME)
        _model = AutoModelForSeq2SeqLM.from_pretrained(_MODEL_NAME)
    return _tokenizer, _model


def fetch_article_text(url: str, min_chars: int = 300) -> str | None:
    if not url:
        return None
    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return None
        text = trafilatura.extract(downloaded)
        if not text or len(text) < min_chars:
            return None
        return text
    except Exception as exc:
        print(f"!! Article fetch failed ({exc})")
        return None


def summarize(text: str) -> str | None:
    try:
        tokenizer, model = _get_model()
        inputs = tokenizer(text[:3000], return_tensors="pt", truncation=True, max_length=1024)
        summary_ids = model.generate(**inputs, max_length=80, min_length=25, num_beams=4)
        return tokenizer.decode(summary_ids[0], skip_special_tokens=True).strip()
    except Exception as exc:
        print(f"!! Summarization failed ({exc})")
        return None


def write_content_caption(url: str) -> str | None:
    """Full pipeline: fetch the real article, then summarize it. Returns None
    on any failure - the caller should fall back to the bare headline."""
    text = fetch_article_text(url)
    if not text:
        return None
    if _is_mostly_telugu(text):
        print("!! Article is Telugu-script - summarizer is English-only, skipping (would produce garbage)")
        return None
    return summarize(text)
