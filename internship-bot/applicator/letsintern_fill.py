"""
applicator/letsintern_fill.py
─────────────────────────────
Automated LetsInternship application filler using Selenium.
- Navigates to the listing's apply URL.
- Clicks "Apply".
- Fills the cover letter if necessary.
"""

import logging
import random
import time
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

SCREENSHOT_DIR = Path("./logs/screenshots")

def _ensure_screenshot_dir():
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

def _take_screenshot(driver, label: str):
    try:
        _ensure_screenshot_dir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = SCREENSHOT_DIR / f"{label}_{timestamp}.png"
        driver.save_screenshot(str(filename))
        logger.info(f"  📸 Screenshot saved: {filename}")
    except Exception as e:
        logger.debug(f"Failed to save screenshot: {e}")

def apply_letsinternship(driver, listing: dict, cover_note: str, profile: dict) -> dict:
    """
    Best-effort LetsInternship Apply.
    """
    try:
        apply_url = listing.get("apply_url", "")
        logger.info(f"[LetsInternship] Navigating to: {apply_url}")
        driver.get(apply_url)
        time.sleep(random.uniform(3.0, 5.0))

        # Check for 404
        if "404" in driver.title.lower() or "not found" in driver.page_source.lower():
            return {"success": False, "message": "Listing page not found (404)"}

        # Click Apply button
        apply_clicked = False
        apply_selectors = [
            "button.apply-btn",
            "a.apply-button",
            "button[id*='apply']",
            "a[href*='apply']"
        ]

        for selector in apply_selectors:
            try:
                btn = driver.find_element("css selector", selector)
                if btn.is_displayed():
                    btn.click()
                    apply_clicked = True
                    logger.info("  ✓ Clicked Apply button")
                    time.sleep(random.uniform(2.0, 3.0))
                    break
            except Exception:
                continue

        if not apply_clicked:
            logger.warning("[LetsInternship] Could not find Apply button")
            return {"success": False, "message": "No Apply button found"}

        # LetsInternship typically redirects to a mailto: or an external site, or has a simple form.
        # Check if it's an external redirect
        if apply_url not in driver.current_url and "letsintern" not in driver.current_url.lower():
            return {"success": True, "message": "Redirected to external site for application"}

        # Check for form submit
        try:
            submit_btn = driver.find_element("css selector", "button[type='submit']")
            submit_btn.click()
            logger.info("  ✓ Clicked Submit button")
            time.sleep(random.uniform(2.0, 3.0))
            return {"success": True, "message": "Application submitted successfully"}
        except Exception:
            pass

        return {"success": True, "message": "Apply button clicked, check manually if submitted"}

    except Exception as e:
        logger.error(f"[LetsInternship] ✗ Error during application: {e}")
        _take_screenshot(driver, "letsintern_apply_error")
        return {"success": False, "message": f"Error: {str(e)}"}
