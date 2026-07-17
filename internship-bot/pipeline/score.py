"""
pipeline/score.py
─────────────────
Stage 2 of the ApplyFlow pipeline: AI scoring / filtering.

Independently testable — no browser, no side effects.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def run_score(listings: list[dict], profile: dict) -> tuple[list[dict], int]:
    """
    Score all listings with the AI filter and return only approved ones.

    Args:
        listings: Fresh listings from run_discover().
        profile:  Validated candidate profile dict.

    Returns:
        (approved_listings, skipped_count)
    """
    from agent.filter import filter_listings

    logger.info("[Score] Scoring %d listing(s) …", len(listings))

    try:
        approved = filter_listings(listings, profile)
    except Exception as exc:
        logger.error("[Score] AI filter crashed: %s", exc)
        return [], len(listings)

    skipped = len(listings) - len(approved)
    logger.info("[Score] %d approved, %d skipped (score too low)", len(approved), skipped)
    return approved, skipped
