"""
notifier/ntfy.py
────────────────
ntfy.sh push notifications for instant alerts.
"""

import os
import requests
import logging

logger = logging.getLogger(__name__)

def send_instant(message: str, tags: str = "rocket", priority: str = "default"):
    """
    Send an instant push notification via ntfy.sh
    """
    topic = os.getenv("NTFY_TOPIC", "")
    if not topic or topic == "your_random_topic_here":
        return

    try:
        url = f"https://ntfy.sh/{topic}"
        headers = {
            "Title": "ApplyFlow",
            "Priority": priority,
            "Tags": tags
        }
        resp = requests.post(url, data=message.encode("utf-8"), headers=headers, timeout=10)
        if resp.status_code != 200:
            logger.warning(f"[Ntfy] ✗ Failed to send notification: {resp.text}")
    except Exception as e:
        logger.warning(f"[Ntfy] ✗ Request failed: {e}")
