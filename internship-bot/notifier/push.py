"""
notifier/push.py
────────────────
ntfy.sh push notifications for instant alerts and summaries.
"""

import os
import requests
import logging

logger = logging.getLogger(__name__)

def _send_message(topic: str, message: str, tags: str = "rocket", priority: str = "default") -> bool:
    try:
        url = f"https://ntfy.sh/{topic}"
        headers = {
            "Title": "ApplyFlow",
            "Priority": priority,
            "Tags": tags
        }
        resp = requests.post(url, data=message.encode("utf-8"), headers=headers, timeout=10)
        if resp.status_code == 200:
            return True
        else:
            logger.warning(f"[Ntfy] ✗ Failed to send notification: {resp.text}")
            return False
    except Exception as e:
        logger.warning(f"[Ntfy] ✗ Request failed: {e}")
        return False

def send_instant(message: str, tags: str = "rocket", priority: str = "default"):
    """
    Send an instant push notification via ntfy.sh
    """
    topic = os.getenv("NTFY_TOPIC", "")
    if not topic or topic == "your_random_topic_here":
        return

    _send_message(topic, message, tags, priority)

def send_summary(applied: list[dict], skipped: int, errors: int, manual: list[dict] = None):
    """
    Send a daily summary report via ntfy.sh
    """
    topic = os.getenv("NTFY_TOPIC", "")
    
    if not topic:
        logger.info("[Ntfy] Not configured (no NTFY_TOPIC) — skipping notification")
        return
        
    if topic == "your_random_topic_here":
        logger.info("[Ntfy] Topic is placeholder value — skipping")
        return

    applied_count = len(applied)

    lines = [
        "🤖 Internship Bot Report",
        "",
        f"✅ Applied: {applied_count}",
        f"⏭ Skipped: {skipped}",
        f"❌ Errors: {errors}",
    ]

    if applied:
        lines.append("")
        lines.append("Companies applied to:")
        for listing in applied:
            company = listing.get("company", "Unknown")
            role = listing.get("title", "N/A")
            lines.append(f"• {company} — {role}")
    else:
        lines.append("")
        lines.append("ℹ️ No new applications today.")

    if manual:
        lines.append("")
        lines.append("⚠️ Needs Manual Review:")
        for listing in manual:
            company = listing.get("company", "Unknown")
            role = listing.get("title", "N/A")
            lines.append(f"• {company} — {role}")

    message = "\n".join(lines)
    logger.info(f"[Ntfy] Sending summary ({applied_count} applied, {skipped} skipped)…")

    success = _send_message(topic, message, tags="clipboard,robot", priority="default")
    if success:
        logger.info("[Ntfy] ✅ Summary sent successfully")
    else:
        logger.warning("[Ntfy] ✗ Could not send summary")
