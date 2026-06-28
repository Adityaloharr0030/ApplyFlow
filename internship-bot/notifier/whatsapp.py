"""
notifier/whatsapp.py
────────────────────
WhatsApp notification module using CallMeBot API.
"""

import logging
import os
import requests
import urllib.parse

logger = logging.getLogger(__name__)

def _send_message(phone: str, apikey: str, text: str) -> bool:
    try:
        encoded_text = urllib.parse.quote(text)
        url = f"https://api.callmebot.com/whatsapp.php?phone={phone}&text={encoded_text}&apikey={apikey}"
        resp = requests.get(url, timeout=10)
        
        if resp.status_code == 200:
            return True
        else:
            logger.warning(f"[WhatsApp] ✗ API returned status {resp.status_code}: {resp.text[:200]}")
            return False
    except Exception as e:
        logger.warning(f"[WhatsApp] ✗ HTTP request failed: {e}")
        return False

def send_instant(message: str):
    """
    Send an instant real-time notification to WhatsApp.
    """
    phone = os.getenv("WHATSAPP_PHONE", "")
    apikey = os.getenv("WHATSAPP_API_KEY", "")
    
    if not phone or not apikey or phone == "your_phone_here" or apikey == "your_apikey_here":
        return
        
    _send_message(phone, apikey, message)

def send_summary(applied: list[dict], skipped: int, errors: int, manual: list[dict] = None):
    """
    Send a daily summary report to WhatsApp.
    """
    phone = os.getenv("WHATSAPP_PHONE", "")
    apikey = os.getenv("WHATSAPP_API_KEY", "")

    if not phone or not apikey:
        logger.info("[WhatsApp] Not configured (no WHATSAPP_PHONE or WHATSAPP_API_KEY) — skipping notification")
        return

    if phone == "your_phone_here" or apikey == "your_apikey_here":
        logger.info("[WhatsApp] Credentials are placeholder values — skipping")
        return

    applied_count = len(applied)

    lines = [
        "🤖 *Internship Bot Report*",
        "",
        f"✅ Applied: {applied_count}",
        f"⏭ Skipped: {skipped}",
        f"❌ Errors: {errors}",
    ]

    if applied:
        lines.append("")
        lines.append("*Companies applied to:*")
        for listing in applied:
            company = listing.get("company", "Unknown")
            role = listing.get("title", "N/A")
            lines.append(f"• {company} — {role}")
    else:
        lines.append("")
        lines.append("ℹ️ No new applications today.")

    if manual:
        lines.append("")
        lines.append("*⚠️ Needs Manual Review:*")
        for listing in manual:
            company = listing.get("company", "Unknown")
            role = listing.get("title", "N/A")
            lines.append(f"• {company} — {role}")

    message = "\n".join(lines)
    logger.info(f"[WhatsApp] Sending summary ({applied_count} applied, {skipped} skipped)…")

    success = _send_message(phone, apikey, message)
    if success:
        logger.info("[WhatsApp] ✅ Summary sent successfully")
    else:
        logger.warning("[WhatsApp] ✗ Could not send summary — check phone number and apikey")
