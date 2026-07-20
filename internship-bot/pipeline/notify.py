"""
pipeline/notify.py
──────────────────
Stage 4 of the ApplyFlow pipeline: fire summary notifications.

Independently testable — no browser, no AI.
"""

import logging

logger = logging.getLogger(__name__)


def run_notify(
    applied: list[dict],
    manual: list[dict],
    skipped: int,
    errors: int,
) -> None:
    """
    Send end-of-run summary to Telegram, ntfy, and WhatsApp.
    Failures are logged but never raise — the pipeline must not crash here.
    """
    from notifier.telegram import (
        send_summary as telegram_summary,
        send_document as telegram_document,
    )
    from notifier.push import send_summary as ntfy_summary
    from notifier.whatsapp import send_summary as whatsapp_summary

    logger.info("[Notify] Sending summary — applied=%d, manual=%d, skipped=%d, errors=%d",
                len(applied), len(manual), skipped, errors)

    for label, fn, *extra in [
        ("Telegram",  telegram_summary, applied, skipped, errors, manual),
        ("ntfy",      ntfy_summary,     applied, skipped, errors, manual),
        ("WhatsApp",  whatsapp_summary, applied, skipped, errors, manual),
    ]:
        try:
            fn(*extra)
        except Exception as exc:
            logger.warning("[Notify] %s summary failed: %s", label, exc)

    # Send a CSV log containing ONLY this run's data
    import csv
    from pathlib import Path
    from datetime import datetime
    
    try:
        latest_csv = Path("logs/latest_run.csv")
        latest_csv.parent.mkdir(parents=True, exist_ok=True)
        
        headers = ["Date", "Company", "Role", "Location", "Source", "Status", "Score", "Apply URL", "Cover Note Preview"]
        
        with open(latest_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            for listing in applied:
                writer.writerow([
                    now_str,
                    listing.get("company", "Unknown"),
                    listing.get("title", "N/A"),
                    listing.get("location", "N/A"),
                    listing.get("source", "N/A"),
                    "Applied ✓",
                    str(listing.get("score", "N/A")),
                    listing.get("apply_url", "N/A"),
                    "See dashboard/sheets for full cover note"
                ])
                
            for listing in manual:
                writer.writerow([
                    now_str,
                    listing.get("company", "Unknown"),
                    listing.get("title", "N/A"),
                    listing.get("location", "N/A"),
                    listing.get("source", "N/A"),
                    "Pending (Manual)",
                    str(listing.get("score", "N/A")),
                    listing.get("apply_url", "N/A"),
                    "N/A"
                ])
                
        if len(applied) > 0 or len(manual) > 0:
            telegram_document(str(latest_csv))
    except Exception as exc:
        logger.debug("[Notify] Telegram fresh CSV attachment failed: %s", exc)


def fire_instant(platform: str, listing: dict, is_error: bool = False, error_msg: str = "") -> None:
    """
    Fire an instant (per-application) notification.
    Called immediately after each successful or failed application.
    """
    from notifier.telegram import send_instant as telegram_instant
    from notifier.push import send_instant as ntfy_instant
    from notifier.whatsapp import send_instant as whatsapp_instant

    if is_error:
        msg  = f"⚠️ {platform.capitalize()} error: {error_msg}"
        tags = "warning"
    else:
        title    = listing.get("title", "Role")
        company  = listing.get("company", "Company")
        location = listing.get("location", "Not specified")
        score    = listing.get("score", "?")
        reason   = listing.get("reason", "N/A")
        url      = listing.get("apply_url", "")
        msg = (
            f"✅ APPLIED: {title}\n"
            f"🏢 Company: {company}\n"
            f"📍 Location: {location}\n"
            f"🌐 Platform: {platform.capitalize()}\n"
            f"🎯 AI Score: {score}/10\n"
            f"💡 Why: {reason}\n"
            f"🔗 Link: {url}"
        )
        tags = "rocket"

    for label, fn in [("Telegram", telegram_instant), ("ntfy", ntfy_instant), ("WhatsApp", whatsapp_instant)]:
        try:
            if label == "ntfy":
                fn(msg, tags=tags)  # only ntfy's send_instant accepts `tags`
            else:
                fn(msg)             # Telegram and WhatsApp take message only
        except Exception as exc:
            logger.debug("[Notify] %s instant failed: %s", label, exc)
