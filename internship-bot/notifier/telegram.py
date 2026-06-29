"""
notifier/telegram.py
────────────────────
Telegram bot notification module.
- Sends a daily summary of the bot's activity
- Shows count of applied, skipped, and errored listings
- Lists each company the bot applied to
- Fails silently if Telegram is not configured
"""

import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)



def _send_message_requests(bot_token: str, chat_id: str, text: str) -> bool:
    """
    Fallback: send a Telegram message using the raw HTTP API (no async needed).
    """
    try:
        import requests

        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
        }
        resp = requests.post(url, json=payload, timeout=15)
        if resp.status_code == 200:
            return True
        else:
            logger.warning(
                f"[Telegram] ✗ API returned status {resp.status_code}: {resp.text[:200]}"
            )
            return False
    except Exception as e:
        logger.warning(f"[Telegram] ✗ HTTP request failed: {e}")
        return False

def send_instant(message: str):
    """
    Send an instant real-time notification to Telegram.
    """
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    if not bot_token or not chat_id or bot_token == "your_bot_token_here" or chat_id == "your_chat_id_here":
        return
    _send_message_requests(bot_token, chat_id, message)

def send_document(file_path: str):
    """
    Send a document (e.g. CSV/Excel file) to Telegram.
    """
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    if not bot_token or not chat_id or bot_token == "your_bot_token_here" or chat_id == "your_chat_id_here":
        return
    
    if not os.path.exists(file_path):
        logger.warning(f"[Telegram] Document not found: {file_path}")
        return

    try:
        import requests
        url = f"https://api.telegram.org/bot{bot_token}/sendDocument"
        payload = {"chat_id": chat_id}
        with open(file_path, "rb") as f:
            files = {"document": f}
            resp = requests.post(url, data=payload, files=files, timeout=30)
            
        if resp.status_code == 200:
            logger.info(f"[Telegram] ✅ Document {os.path.basename(file_path)} sent successfully")
        else:
            logger.warning(f"[Telegram] ✗ Failed to send document: {resp.text[:200]}")
    except Exception as e:
        logger.warning(f"[Telegram] ✗ Error sending document: {e}")

def send_summary(applied: list[dict], skipped: int, errors: int, manual: list[dict] = None):
    """
    Send a daily summary report to Telegram.

    Args:
        applied: List of listing dicts that were successfully applied to.
                 Each should have 'company' and 'title' keys.
        skipped: Number of listings skipped (low score / already applied).
        errors:  Number of application errors.
    """
    # Get Telegram credentials from .env
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")

    if not bot_token or not chat_id:
        logger.info(
            "[Telegram] Telegram not configured (no BOT_TOKEN or CHAT_ID) — skipping notification"
        )
        return

    if bot_token == "your_bot_token_here" or chat_id == "your_chat_id_here":
        logger.info("[Telegram] Telegram credentials are placeholder values — skipping")
        return

    # Build the summary message
    today = datetime.now().strftime("%d %B %Y")
    applied_count = len(applied)

    # Header
    lines = [
        f"🤖 <b>Internship Bot Report — {today}</b>",
        "",
        f"✅ Applied: <b>{applied_count}</b>",
        f"⏭ Skipped: <b>{skipped}</b>",
        f"❌ Errors: <b>{errors}</b>",
    ]

    # List applied companies
    if applied:
        lines.append("")
        lines.append("<b>Companies applied to:</b>")
        for listing in applied:
            company = listing.get("company", "Unknown")
            role = listing.get("title", "N/A")
            source = listing.get("source", "")
            lines.append(f"• {company} — {role} [{source}]")
    else:
        lines.append("")
        lines.append("ℹ️ No new applications today.")

    if manual:
        lines.append("")
        lines.append("<b>⚠️ Needs Manual Review:</b>")
        for listing in manual:
            company = listing.get("company", "Unknown")
            role = listing.get("title", "N/A")
            lines.append(f"• {company} — {role}")

    # Footer
    lines.append("")
    lines.append("🔄 Next run scheduled for tomorrow at 9:00 AM")

    message = "\n".join(lines)

    # Try sending the message
    logger.info(f"[Telegram] Sending summary ({applied_count} applied, {skipped} skipped)…")

    # Method 1: Use requests (simpler, synchronous)
    success = _send_message_requests(bot_token, chat_id, message)

    if success:
        logger.info("[Telegram] ✅ Summary sent successfully")
    else:
        logger.warning("[Telegram] ✗ Could not send summary — check bot token and chat ID")
