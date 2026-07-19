import requests
import logging

logger = logging.getLogger(__name__)
API_URL = "http://127.0.0.1:8000/api/session/update"

def push_update(
    status: str = "running",
    current_platform: str = "",
    current_listing: str = "",
    current_step: str = "",
    applied_count: int = 0,
    skipped_count: int = 0,
    error_count: int = 0,
    event: dict = None
):
    try:
        payload = {
            "status": status,
            "current_platform": current_platform,
            "current_listing": current_listing,
            "current_step": current_step,
            "applied_count": applied_count,
            "skipped_count": skipped_count,
            "error_count": error_count,
            "event": event
        }
        requests.post(API_URL, json=payload, timeout=2)
    except Exception as e:
        logger.debug(f"Failed to push live update: {e}")
