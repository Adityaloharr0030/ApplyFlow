"""
platforms/indeed.py
───────────────────
Adapter for Indeed.
Uses python-jobspy for scraping, and Selenium for Indeed Apply.
"""

import logging
import random
import time
import os
from typing import Any
from .base import Platform

logger = logging.getLogger(__name__)

class IndeedPlatform(Platform):
    def __init__(self):
        super().__init__()

    def search(self, profile: dict) -> list[dict]:
        if self.blocked:
            return []

        try:
            from jobspy import scrape_jobs
        except ImportError:
            logger.error("[Indeed] python-jobspy not installed. Cannot scrape Indeed.")
            return []

        search_term = profile.get("keywords", ["internship"])[0]
        location = profile.get("countries", ["India"])[0]
        
        logger.info(f"[Indeed] Searching via jobspy: term='{search_term}', location='{location}'")

        try:
            # scrape_jobs returns a pandas DataFrame
            jobs = scrape_jobs(
                site_name=["indeed"],
                search_term=search_term,
                location=location,
                results_wanted=15,
                country_indeed=location.lower()
            )

            listings = []
            for _, row in jobs.iterrows():
                listings.append({
                    "title": str(row.get("title", "Unknown")),
                    "company": str(row.get("company", "Unknown")),
                    "location": str(row.get("location", "Not specified")),
                    "apply_url": str(row.get("job_url", "")),
                    "source": "indeed",
                    "description": str(row.get("description", ""))
                })
            
            logger.info(f"[Indeed] ✓ Found {len(listings)} listing(s)")
            return listings
        except Exception as e:
            logger.warning(f"[Indeed] ✗ Search failed: {e}")
            return []

    def apply(self, listing: dict, cover_note: str, profile: dict, driver: Any) -> dict:
        if self.blocked:
            return {"success": False, "message": "Platform blocked by circuit breaker"}

        try:
            if os.getenv("DRY_RUN", "false").lower() == "true":
                logger.info(f"  [DRY RUN] Would apply to {listing.get('title')} @ {listing.get('company')}")
                return {"success": True, "message": "Dry run — not submitted"}

            apply_url = listing.get("apply_url", "")
            logger.info(f"[Indeed] Navigating to: {apply_url}")
            driver.get(apply_url)
            time.sleep(random.uniform(3.0, 5.0))

            if "captcha" in driver.page_source.lower() or "cloudflare" in driver.title.lower():
                if os.getenv("HEADLESS", "true").lower() == "false":
                    logger.warning("  ⚠️ Captcha detected! You have 30 seconds to solve it manually in the browser...")
                    for _ in range(10):
                        time.sleep(3)
                        if "captcha" not in driver.page_source.lower() and "cloudflare" not in driver.title.lower():
                            logger.info("  ✓ Captcha solved! Continuing...")
                            break
                    else:
                        self.record_captcha()
                        return {"success": False, "message": "Hit CAPTCHA / Cloudflare wall (Timeout)"}
                else:
                    self.record_captcha()
                    return {"success": False, "message": "Hit CAPTCHA / Cloudflare wall"}

            # Check if it's "Indeed Apply" vs external redirect
            try:
                apply_btn = driver.find_element("css selector", "#indeedApplyButton")
                apply_btn.click()
                logger.info("  ✓ Clicked Indeed Apply button")
                time.sleep(random.uniform(2.0, 4.0))
            except Exception:
                logger.warning("[Indeed] External site or manual apply required. Logging as manual.")
                return {"success": False, "message": "External ATS redirect (Manual apply)"}

            # Switch to iframe if the Indeed Apply modal opens
            try:
                iframe = driver.find_element("css selector", "iframe[title*='Indeed Apply']")
                driver.switch_to.frame(iframe)
            except Exception:
                pass # it might not be an iframe

            # Simple linear loop to get through the form
            max_steps = 5
            for step in range(max_steps):
                try:
                    # Look for "Continue" or "Submit" buttons
                    continue_btn = None
                    buttons = driver.find_elements("css selector", "button")
                    for btn in buttons:
                        text = btn.text.lower()
                        if "submit" in text or "apply" in text and "indeed" not in text:
                            btn.click()
                            logger.info("  ✓ Clicked Submit")
                            time.sleep(random.uniform(3.0, 5.0))
                            self.captcha_count = 0
                            return {"success": True, "message": "Indeed Application submitted successfully"}
                        elif "continue" in text:
                            continue_btn = btn

                    if continue_btn:
                        continue_btn.click()
                        logger.info(f"  ✓ Clicked Continue (Step {step+1})")
                        time.sleep(random.uniform(2.0, 3.0))
                    else:
                        break
                except Exception as e:
                    logger.debug(f"[Indeed] Step {step} failed: {e}")
                    pass

            driver.switch_to.default_content()
            return {"success": False, "message": "Form too complex (exceeded max steps)"}

        except Exception as e:
            logger.error(f"[Indeed] ✗ Error during application: {e}")
            return {"success": False, "message": f"Error: {str(e)}"}
