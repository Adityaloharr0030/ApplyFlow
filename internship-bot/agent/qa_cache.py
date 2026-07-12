"""
agent/qa_cache.py
─────────────────
Q&A Answer Cache for screening questions.
Stores previously generated answers and reuses them for consistency.

Like ApplyCove: "For custom questions ApplyCove has not seen before, it generates
a context-aware answer and stores the answer for future reuse so subsequent
applications get the same answer consistently."
"""

import json
import logging
from difflib import SequenceMatcher
from pathlib import Path

logger = logging.getLogger(__name__)

CACHE_FILE = Path("./data/qa_cache.json")
FUZZY_THRESHOLD = 0.85  # 85% similarity = same question


def _load_cache() -> dict:
    """Load the Q&A cache from disk."""
    try:
        if CACHE_FILE.exists():
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.debug(f"[QACache] Failed to load cache: {e}")
    return {}


def _save_cache(cache: dict):
    """Save the Q&A cache to disk."""
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"[QACache] Failed to save cache: {e}")


def _normalize(text: str) -> str:
    """Normalize question text for comparison."""
    return " ".join(text.lower().strip().split())


def _similarity(a: str, b: str) -> float:
    """Compute similarity ratio between two strings."""
    return SequenceMatcher(None, _normalize(a), _normalize(b)).ratio()


def get_cached_answer(question: str) -> str | None:
    """
    Look up a cached answer for the given question.
    Uses fuzzy matching — if a question is >= 85% similar to a cached one,
    returns the cached answer.
    """
    if not question or len(question.strip()) < 5:
        return None

    cache = _load_cache()
    normalized_q = _normalize(question)

    # Exact match first
    if normalized_q in cache:
        logger.info(f"[QACache] Exact hit: {question[:40]}...")
        return cache[normalized_q]

    # Fuzzy match
    best_match = None
    best_score = 0.0

    for cached_q, cached_a in cache.items():
        score = _similarity(question, cached_q)
        if score > best_score:
            best_score = score
            best_match = cached_a

    if best_score >= FUZZY_THRESHOLD and best_match:
        logger.info(f"[QACache] Fuzzy hit ({best_score:.0%}): {question[:40]}...")
        return best_match

    return None


def cache_answer(question: str, answer: str):
    """
    Store a question-answer pair in the cache for future reuse.
    """
    if not question or not answer or len(question.strip()) < 5:
        return

    cache = _load_cache()
    normalized_q = _normalize(question)
    cache[normalized_q] = answer.strip()
    _save_cache(cache)
    logger.debug(f"[QACache] Cached answer for: {question[:40]}...")


def get_cache_stats() -> dict:
    """Return stats about the Q&A cache."""
    cache = _load_cache()
    return {
        "total_entries": len(cache),
        "file_path": str(CACHE_FILE),
    }
