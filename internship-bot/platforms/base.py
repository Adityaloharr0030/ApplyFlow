"""
platforms/base.py
─────────────────
Abstract base classes for Platforms.
"""

from abc import ABC, abstractmethod
from typing import Any, List
import logging

logger = logging.getLogger(__name__)

class Platform(ABC):
    """
    Base class for all application platforms (e.g., Internshala, LinkedIn, Indeed).
    Handles circuit breaking logic.
    """
    def __init__(self):
        self.name = self.__class__.__name__.replace("Platform", "").lower()
        self.captcha_count = 0
        self.blocked = False

    def check_circuit_breaker(self):
        if self.captcha_count >= 3:
            if not self.blocked:
                self.blocked = True
                logger.warning(f"[{self.name}] ⚠️ Blocked after repeated CAPTCHA/errors. Pausing for today.")
                # We can fire an instant notification from the orchestrator if this becomes True.
        return self.blocked

    def record_captcha(self):
        self.captcha_count += 1
        self.check_circuit_breaker()

    @abstractmethod
    def search(self, profile: dict) -> List[dict]:
        """
        Scrape internship/job listings.
        Returns a list of dictionaries representing listings.
        """
        pass

    @abstractmethod
    def apply(self, listing: dict, cover_note: str, profile: dict, driver: Any) -> dict:
        """
        Attempt to apply to the listing.
        Returns a dictionary: {"success": bool, "message": str}
        """
        pass
