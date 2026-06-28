"""
applicator/linkedin_fill.py
───────────────────────────
Automated LinkedIn Easy Apply application filler using Selenium.
- Logs in to LinkedIn once.
- Navigates to the listing's apply URL.
- Clicks "Easy Apply".
- Clicks "Next" through the form until "Submit" is found.
"""

import logging
import os
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



def apply_linkedin(driver, listing: dict, cover_note: str, profile: dict) -> dict:
    """
    Best-effort LinkedIn Easy Apply.
    """
    try:
        apply_url = listing.get("apply_url", "")
        logger.info(f"[LinkedIn] Navigating to: {apply_url}")
        driver.get(apply_url)
        time.sleep(random.uniform(3.0, 5.0))

        # Check if Easy Apply is available
        try:
            easy_apply_btn = driver.find_element("css selector", "button.jobs-apply-button")
            easy_apply_btn.click()
            logger.info("  ✓ Clicked Easy Apply button")
            time.sleep(random.uniform(2.0, 3.0))
        except Exception:
            logger.warning("[LinkedIn] Could not find Easy Apply button (might be standard apply)")
            return {"success": False, "message": "No Easy Apply button found"}

        # Loop through "Next" buttons until "Submit" or "Review" appears
        max_steps = 5
        for step in range(max_steps):
            try:
                # Try to find Review or Submit
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
                    
                    return {"success": True, "message": "LinkedIn Application submitted successfully"}
                
                # If no submit, find "Next"
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
        _take_screenshot(driver, "linkedin_apply_error")
        return {"success": False, "message": f"Error: {str(e)}"}
