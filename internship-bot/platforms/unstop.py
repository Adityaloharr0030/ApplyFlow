"""
platforms/unstop.py
───────────────────
Adapter for Unstop.
Uses the public JSON API for scraping, and Selenium for applying.
"""

import logging
import random
import time
import os
import requests
from typing import Any
from .base import Platform

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
}

class UnstopPlatform(Platform):
    def __init__(self):
        super().__init__()

    def search(self, profile: dict) -> list[dict]:
        if self.blocked:
            return []
            
        keyword = profile.get("keywords", ["internship"])[0]
        url = f"https://unstop.com/api/public/opportunity/search-result?opportunity=internships&keyword={keyword}&page=1"

        logger.info(f"[Unstop] Searching JSON API: keyword={keyword}")

        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            
            data = resp.json()
            items = data.get("data", {}).get("data", [])
            
            listings: list[dict] = []

            for item in items:
                title = item.get("title")
                company = item.get("organization", {}).get("name") or item.get("seo_url")
                apply_url = f"https://unstop.com/{item.get('seo_url')}"
                
                if title and apply_url:
                    listings.append({
                        "title": title,
                        "company": company,
                        "location": item.get("location", "Not specified"),
                        "apply_url": apply_url,
                        "source": "unstop",
                    })

            logger.info(f"[Unstop] ✓ Found {len(listings)} listing(s)")
            return listings

        except Exception as e:
            logger.warning(f"[Unstop] ✗ Search failed: {e}")
            return []

    def apply(self, listing: dict, cover_note: str, profile: dict, driver: Any) -> dict:
        if self.blocked:
            return {"success": False, "message": "Platform blocked by circuit breaker"}

        try:
            if os.getenv("DRY_RUN", "false").lower() == "true":
                logger.info(f"  [DRY RUN] Would apply to {listing.get('title')} @ {listing.get('company')}")
                return {"success": True, "message": "Dry run — not submitted"}

            apply_url = listing.get("apply_url", "")
            logger.info(f"[Unstop] Navigating to: {apply_url}")
            driver.get(apply_url)
            time.sleep(random.uniform(3.0, 5.0))

            if "login" in driver.current_url.lower():
                self.record_captcha()
                return {"success": False, "message": "Hit Login wall"}

            # Look for apply button
            apply_selectors = ["button.btn-apply", "a.btn-apply", "button[title='Apply']"]
            apply_clicked = False
            for selector in apply_selectors:
                try:
                    btn = driver.find_element("css selector", selector)
                    btn.click()
                    logger.info("  ✓ Clicked Apply button")
                    apply_clicked = True
                    time.sleep(random.uniform(2.0, 3.0))
                    break
                except Exception:
                    continue
                    
            if not apply_clicked:
                return {"success": False, "message": "No Apply button found (Manual apply required)"}

            # If there's a modal to confirm
            try:
                submit_btn = driver.find_element("css selector", "button.submit-btn, button[type='submit']")
                submit_btn.click()
                time.sleep(random.uniform(2.0, 3.0))
                self.captcha_count = 0
                return {"success": True, "message": "Unstop Application submitted successfully"}
            except Exception:
                # Often unstop apply is just 1 click if already registered
                self.captcha_count = 0
                return {"success": True, "message": "Unstop Application likely submitted (1-click)"}

        except Exception as e:
            logger.error(f"[Unstop] ✗ Error during application: {e}")
            return {"success": False, "message": f"Error: {str(e)}"}
