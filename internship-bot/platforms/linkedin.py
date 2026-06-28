"""
platforms/linkedin.py
─────────────────────
Adapter for LinkedIn.
Uses the guest jobs API for scraping (no login needed), and Selenium for Easy Apply.
"""

import logging
import random
import time
import os
import requests
from bs4 import BeautifulSoup
from typing import Any
from .base import Platform

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

class LinkedInPlatform(Platform):
    def __init__(self):
        super().__init__()

    def search(self, profile: dict) -> list[dict]:
        if self.blocked:
            return []
            
        keywords = "+".join(profile.get("keywords", ["internship"])[:3])
        url = (
            f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
            f"?keywords={keywords}&location=India&f_WT=2&start=0"
        )

        logger.info(f"[LinkedIn] Searching guest API: keywords={keywords}")

        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")
            listings: list[dict] = []

            for card in soup.select("li"):
                title_el = card.select_one(".base-search-card__title")
                company_el = card.select_one(".base-search-card__subtitle")
                location_el = card.select_one(".job-search-card__location")
                link_el = card.select_one("a.base-card__full-link")

                if title_el and link_el:
                    listings.append({
                        "title": title_el.get_text(strip=True),
                        "company": company_el.get_text(strip=True) if company_el else "Unknown",
                        "location": location_el.get_text(strip=True) if location_el else "Not specified",
                        "apply_url": link_el["href"].split("?")[0],
                        "source": "linkedin",
                    })

                if len(listings) >= 15: # slightly bump up limit to find more
                    break

            logger.info(f"[LinkedIn] ✓ Found {len(listings)} listing(s)")
            return listings

        except Exception as e:
            logger.warning(f"[LinkedIn] ✗ Search failed: {e}")
            return []

    def apply(self, listing: dict, cover_note: str, profile: dict, driver) -> dict:
        if self.blocked:
            return {"success": False, "message": "Platform blocked by circuit breaker"}

        try:
            if os.getenv("DRY_RUN", "false").lower() == "true":
                logger.info(f"  [DRY RUN] Would apply to {listing.get('title')} @ {listing.get('company')}")
                return {"success": True, "message": "Dry run — not submitted"}

            apply_url = listing.get("apply_url", "")
            logger.info(f"[LinkedIn] Navigating to: {apply_url}")
            driver.get(apply_url)
            time.sleep(random.uniform(3.0, 5.0))

            # Circuit breaker trigger for LinkedIn restricts
            if "login" in driver.current_url.lower() and "captcha" in driver.page_source.lower():
                self.record_captcha()
                return {"success": False, "message": "Hit CAPTCHA / Login wall"}

            try:
                easy_apply_btn = driver.find_element("css selector", "button.jobs-apply-button")
                easy_apply_btn.click()
                logger.info("  ✓ Clicked Easy Apply button")
                time.sleep(random.uniform(2.0, 3.0))
            except Exception:
                logger.warning("[LinkedIn] Could not find Easy Apply button. Skipping to Manual.")
                return {"success": False, "message": "No Easy Apply button found (Manual apply required)"}

            # Simple linear loop to get through the form
            max_steps = 5
            for step in range(max_steps):
                try:
                    submit_btn = None
                    buttons = driver.find_elements("css selector", "button")
                    for btn in buttons:
                        text = btn.text.lower()
                        if "submit application" in text or "review" in text:
                            submit_btn = btn
                            break

                    if submit_btn:
                        submit_btn.click()
                        logger.info("  ✓ Clicked Submit/Review")
                        time.sleep(random.uniform(3.0, 5.0))
                        
                        # If it was review, click submit again
                        for btn in driver.find_elements("css selector", "button"):
                            if "submit application" in btn.text.lower():
                                btn.click()
                                logger.info("  ✓ Clicked Final Submit")
                                time.sleep(random.uniform(3.0, 5.0))
                                break
                        
                        self.captcha_count = 0
                        return {"success": True, "message": "LinkedIn Application submitted successfully"}
                    
                    next_btn = None
                    for btn in buttons:
                        if "next" in btn.text.lower():
                            next_btn = btn
                            break
                    
                    if next_btn:
                        next_btn.click()
                        logger.info(f"  ✓ Clicked Next (Step {step+1})")
                        time.sleep(random.uniform(2.0, 3.0))
                    else:
                        return {"success": False, "message": "Stuck on form (No Next or Submit found)"}
                except Exception as e:
                    logger.debug(f"[LinkedIn] Step {step} failed: {e}")
                    pass

            return {"success": False, "message": "Form too complex (exceeded max steps)"}

        except Exception as e:
            logger.error(f"[LinkedIn] ✗ Error during application: {e}")
            return {"success": False, "message": f"Error: {str(e)}"}
