"""Crew registry — maps crew names to runner functions and metadata.

Adding a new crew: add one entry to CREW_REGISTRY.
The Discord bot auto-creates a channel for it on startup.
"""

import re

from src.crew import run_content_crew
from src.quant_crew import run_quant_crew


CREW_REGISTRY: dict[str, dict] = {
    "content": {
        "runner": run_content_crew,
        "description": "Blog posts, landing pages, threads, newsletters",
        "default_args": {"include_seo": True, "include_social": False},
        "emoji": "\U0001f4dd",
    },
    "quant": {
        "runner": run_quant_crew,
        "description": "Stock analysis, financial content",
        "default_args": {},
        "emoji": "\U0001f4ca",
        "extract_tickers": True,
    },
}

# Matches $NVDA, $AAPL, or bare uppercase 2-5 letter words after commas
_TICKER_RE = re.compile(r"\$([A-Z]{1,5})\b")
_COMMA_SEP_RE = re.compile(r"^[A-Z]{1,5}(?:\s*,\s*[A-Z]{1,5})+$")


def extract_tickers(text: str) -> list[str]:
    """Pull stock tickers from message text.

    Recognises $NVDA style cashtags and comma-separated lists like
    'NVDA, AAPL, MSFT'.
    """
    # Cashtag style: $NVDA
    tickers = _TICKER_RE.findall(text)

    # Comma-separated at start of message: "NVDA, AAPL analyze these"
    first_line = text.split("\n")[0].strip()
    for segment in first_line.split(" "):
        segment = segment.strip().rstrip(".")
        if _COMMA_SEP_RE.match(segment):
            tickers.extend(t.strip() for t in segment.split(",") if t.strip())

    # Dedupe preserving order
    seen: set[str] = set()
    result: list[str] = []
    for t in tickers:
        t = t.upper()
        if t not in seen:
            seen.add(t)
            result.append(t)
    return result
