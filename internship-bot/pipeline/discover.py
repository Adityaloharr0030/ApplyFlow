"""
pipeline/discover.py
────────────────────
Stage 1 of the ApplyFlow pipeline: Discover + Deduplicate + Filter Already Applied.

Returns a list of fresh, unique listings ready for AI scoring.
This is independently testable — no browser, no AI, no side effects.
"""

import logging
import os
from collections import defaultdict
from typing import Optional

logger = logging.getLogger(__name__)


def run_discover(profile: dict, platform_filter: Optional[str] = None) -> tuple[list[dict], int]:
    """
    Scrape listings from all configured platforms, deduplicate, and
    strip already-applied URLs.

    Args:
        profile:         Validated candidate profile dict.
        platform_filter: If set, only this platform is scraped (e.g. "linkedin").

    Returns:
        (new_listings, skipped_count)
          new_listings  — fresh listings not yet applied to.
          skipped_count — how many were dropped as duplicates / already applied.
    """
    # Late imports — keeps this module importable without a running browser
    from platforms.internshala import InternshalaPlatform
    from platforms.linkedin import LinkedInPlatform
    from platforms.indeed import IndeedPlatform
    from platforms.unstop import UnstopPlatform
    from platforms.generic_web import GenericWebPlatform
    from platforms.naukri import NaukriPlatform
    from utils.dedup import deduplicate
    from tracker.sheets import get_applied_urls

    platforms = {
        "internshala": InternshalaPlatform(),
        "linkedin":    LinkedInPlatform(),
        "indeed":      IndeedPlatform(),
        "unstop":      UnstopPlatform(),
        "naukri":      NaukriPlatform(),
        "generic_web": GenericWebPlatform(),
    }

    # ── 1. Scrape ──────────────────────────────────────────────────────────────
    all_listings: list[dict] = []
    for name, platform in platforms.items():
        if platform_filter and name != platform_filter:
            continue
        try:
            logger.info("[Discover] Scraping %s …", name)
            results = platform.search(profile)
            all_listings.extend(results)
            logger.info("[Discover] %s → %d listing(s)", name, len(results))
        except Exception as exc:
            logger.error("[Discover] %s scraper crashed: %s", name, exc)

    logger.info("[Discover] Raw total: %d listing(s)", len(all_listings))

    if not all_listings:
        return [], 0

    # ── 2. Deduplicate ─────────────────────────────────────────────────────────
    unique = deduplicate(all_listings)
    dupes_removed = len(all_listings) - len(unique)
    if dupes_removed:
        logger.info("[Discover] Removed %d duplicate(s)", dupes_removed)

    # ── 3. Filter already-applied ──────────────────────────────────────────────
    applied_cache = get_applied_urls()
    new_listings: list[dict] = []
    already_applied = 0
    for listing in unique:
        url = listing.get("apply_url", "")
        if url and url.strip() in applied_cache:
            already_applied += 1
        else:
            new_listings.append(listing)

    skipped_count = dupes_removed + already_applied
    logger.info(
        "[Discover] %d new listing(s) to evaluate (%d already applied, %d dupes)",
        len(new_listings), already_applied, dupes_removed
    )
    return new_listings, skipped_count
