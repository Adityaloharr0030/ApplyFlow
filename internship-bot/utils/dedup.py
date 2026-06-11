"""
utils/dedup.py
──────────────
Deduplication utility for internship listings.
- Removes duplicate listings based on (company + role) combination
- Case-insensitive matching
- Preserves the first occurrence of each unique listing
"""

import logging

logger = logging.getLogger(__name__)


def deduplicate(listings: list[dict]) -> list[dict]:
    """
    Remove duplicate listings based on normalized (company + title) key.

    Args:
        listings: List of listing dicts. Each must have 'company' and 'title' keys.

    Returns:
        Deduplicated list, preserving the first occurrence of each unique pair.
    """
    if not listings:
        return []

    seen: set[str] = set()
    unique: list[dict] = []
    duplicates_removed = 0

    for listing in listings:
        # Build a normalized dedup key from company + title
        company = listing.get("company", "").strip().lower()
        title = listing.get("title", "").strip().lower()

        # Also normalize common variations
        # Remove extra whitespace
        company = " ".join(company.split())
        title = " ".join(title.split())

        dedup_key = f"{company}||{title}"

        if dedup_key not in seen:
            seen.add(dedup_key)
            unique.append(listing)
        else:
            duplicates_removed += 1
            logger.debug(
                f"  ♻️ Duplicate removed: {listing.get('title')} @ {listing.get('company')} "
                f"[{listing.get('source')}]"
            )

    if duplicates_removed > 0:
        logger.info(
            f"[Dedup] Removed {duplicates_removed} duplicate(s) — "
            f"{len(unique)} unique listing(s) remain"
        )
    else:
        logger.info(f"[Dedup] No duplicates found — {len(unique)} listing(s)")

    return unique
