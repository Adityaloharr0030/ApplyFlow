"""
pipeline/apply.py
─────────────────
Stage 3 of the ApplyFlow pipeline: browser-based application submission.

Handles:
  - Chrome driver lifecycle (launch / quit)
  - Platform login
  - Per-listing apply loop with circuit-breaker and daily cap enforcement
  - Cover note generation
  - Application logging to CSV / Google Sheets
"""

import logging
import os
from collections import defaultdict
from typing import Optional

logger = logging.getLogger(__name__)


def run_apply(
    approved_listings: list[dict],
    profile: dict,
    platform_filter: Optional[str] = None,
) -> tuple[list[dict], list[dict], list[dict], int]:
    """
    Apply to all approved listings.

    Args:
        approved_listings: Output of run_score().
        profile:           Validated candidate profile dict.
        platform_filter:   If set, only this platform is processed.

    Returns:
        (applied, manual, dry_run, error_count)
          applied   — listings successfully submitted.
          manual    — listings requiring human follow-up.
          dry_run   — listings skipped due to DRY_RUN=true.
          error_count — number of failed applications.
    """
    from platforms.internshala import InternshalaPlatform
    from platforms.linkedin import LinkedInPlatform
    from platforms.indeed import IndeedPlatform
    from platforms.unstop import UnstopPlatform
    from platforms.generic_web import GenericWebPlatform
    from platforms.naukri import NaukriPlatform
    from platforms.login import LOGIN_HANDLERS
    from agent.cover_note import generate_cover_note
    from agent.interview_prep import generate_interview_prep
    from tracker.sheets import log_application
    from utils.browser import create_driver

    platforms = {
        "internshala": InternshalaPlatform(),
        "linkedin":    LinkedInPlatform(),
        "indeed":      IndeedPlatform(),
        "unstop":      UnstopPlatform(),
        "naukri":      NaukriPlatform(),
        "generic_web": GenericWebPlatform(),
    }

    caps = {
        "internshala": int(os.getenv("INTERNSHALA_MAX_APPLIES", "15")),
        "linkedin":    int(os.getenv("LINKEDIN_MAX_APPLIES", "10")),
        "indeed":      int(os.getenv("INDEED_MAX_APPLIES", "10")),
        "unstop":      int(os.getenv("UNSTOP_MAX_APPLIES", "15")),
        "naukri":      int(os.getenv("NAUKRI_MAX_APPLIES", "15")),
        "generic_web": 20,
    }

    applied:    list[dict] = []
    manual:     list[dict] = []
    dry_run:    list[dict] = []
    error_count = 0
    applied_counts = defaultdict(int)

    is_dry_run = os.getenv("DRY_RUN", "false").lower() == "true"

    # Group by platform — reuse one driver per session
    grouped: dict[str, list[dict]] = defaultdict(list)
    for listing in approved_listings:
        src = listing.get("source", "generic_web")
        if not platform_filter or src == platform_filter:
            grouped[src].append(listing)

    if not grouped:
        logger.info("[Apply] No listings to process after filtering.")
        return applied, manual, dry_run, error_count

    # ── Launch browser ─────────────────────────────────────────────────────────
    driver = create_driver()
    if driver is None:
        logger.error("[Apply] CRITICAL: Failed to launch Chrome. Aborting apply phase.")
        return applied, manual, dry_run, len(approved_listings)

    # ── Login ──────────────────────────────────────────────────────────────────
    logged_in: set[str] = set()
    if not is_dry_run:
        logger.info("[Apply] Logging into platforms …")
        for src in grouped:
            login_fn = LOGIN_HANDLERS.get(src)
            if login_fn:
                try:
                    if login_fn(driver):
                        logged_in.add(src)
                        logger.info("[Apply] Logged in to %s", src)
                    else:
                        logger.warning("[Apply] Login failed for %s — skipping", src)
                except Exception as exc:
                    logger.error("[Apply] Login to %s crashed: %s", src, exc)
            else:
                logged_in.add(src)  # no login required (indeed, generic_web)
    else:
        logged_in = set(grouped.keys())

    # ── Apply loop ─────────────────────────────────────────────────────────────
    try:
        for src, listings in grouped.items():
            platform = platforms.get(src)
            if not platform:
                continue

            if src not in logged_in:
                logger.warning("[Apply] Skipping %s — not logged in", src)
                error_count += len(listings)
                continue

            for listing in listings:
                if platform.check_circuit_breaker():
                    logger.warning("[Apply] Circuit breaker tripped for %s — stopping", src)
                    break

                if applied_counts[src] >= caps.get(src, 10):
                    logger.info("[Apply] Daily cap reached for %s (%d)", src, caps[src])
                    break

                title   = listing.get("title", "N/A")
                company = listing.get("company", "Unknown")
                logger.info("[Apply] → %s @ %s (%s)", title, company, src)

                # Cover note
                try:
                    cover = generate_cover_note(listing, profile)
                except Exception as exc:
                    logger.error("[Apply] Cover note failed: %s", exc)
                    cover = ""

                # Apply
                try:
                    result = platform.apply(listing, cover, profile, driver)
                except Exception as exc:
                    result = {"success": False, "message": str(exc)}

                # Classify result
                if result.get("success"):
                    msg = result.get("message", "").lower()
                    if "dry run" in msg:
                        dry_run.append(listing)
                        status = "Dry Run"
                    elif "manual" in msg or "pending" in msg:
                        manual.append(listing)
                        status = "Pending (Manual)"
                    else:
                        applied.append(listing)
                        applied_counts[src] += 1
                        status = "Applied ✓"
                        # Interview prep (fire-and-forget)
                        try:
                            generate_interview_prep(listing, profile)
                        except Exception:
                            pass
                        logger.info("[Apply] SUCCESS: %s", result.get("message"))
                else:
                    status = f"Error: {result.get('message', 'unknown')}"
                    error_count += 1
                    logger.warning("[Apply] FAILED: %s", result.get("message"))

                # Log to CSV / Sheets
                try:
                    log_application(listing, status, cover)
                except Exception as exc:
                    logger.error("[Apply] Failed to log application: %s", exc)

    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

    logger.info(
        "[Apply] Done — applied=%d, manual=%d, dry_run=%d, errors=%d",
        len(applied), len(manual), len(dry_run), error_count
    )
    return applied, manual, dry_run, error_count
