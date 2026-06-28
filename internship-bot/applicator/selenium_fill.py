"""
applicator/selenium_fill.py
───────────────────────────
Automated Internshala application filler using Selenium + undetected-chromedriver.
- Logs in to Internshala
- Navigates to the listing's apply URL
- Clicks "Apply Now"
- Fills the cover letter textarea
- Submits the form
- Screenshots on failure (saved to ./logs/screenshots/)
"""

import logging
import os
import random
import time
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Directory for failure screenshots
SCREENSHOT_DIR = Path("./logs/screenshots")

def _ensure_screenshot_dir():
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

def _take_screenshot(driver, label: str):
    """Save a screenshot with timestamp for debugging."""
    try:
        _ensure_screenshot_dir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = SCREENSHOT_DIR / f"{label}_{timestamp}.png"
        driver.save_screenshot(str(filename))
        logger.info(f"  📸 Screenshot saved: {filename}")
    except Exception as e:
        logger.debug(f"Failed to save screenshot: {e}")


def _ensure_screenshot_dir():
    """Create the screenshots directory if it doesn't exist."""
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


def create_driver():
    """
    Hijack the user's actual Chrome profile. 
    Kills any existing Chrome instances first, then launches with undetected_chromedriver
    using the default User Data directory so all logins are preserved.
    """
    try:
        import os
        import undetected_chromedriver as uc
        from pathlib import Path

        logger.info("[Selenium] Force-closing existing Chrome processes...")
        os.system("taskkill /F /IM chrome.exe /T >nul 2>&1")
        import time
        time.sleep(2) # Give it a moment to fully close

        options = uc.ChromeOptions()
        # Point to the user's actual Chrome profile
        user_data_dir = r"C:\Users\ADITYA\AppData\Local\Google\Chrome\User Data"
        options.add_argument(f"--user-data-dir={user_data_dir}")
        options.add_argument("--profile-directory=Default")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")

        # Read from env var — defaults to headless ON
        if os.getenv("HEADLESS", "true").lower() != "false":
            options.add_argument("--headless=new")

        logger.info("[Selenium] Launching undetected_chromedriver with user's default profile...")
        driver = uc.Chrome(options=options, use_subprocess=True)
        driver.implicitly_wait(10)
        
        logger.info("[Selenium] Successfully hijacked default Chrome profile!")
        return driver
    except Exception as e:
        logger.error(f"[SeleniumFill] Failed to hijack Chrome: {e}")
        return None


def apply_internshala(driver, listing: dict, cover_note: str, profile: dict) -> dict:
    """
    Auto-fill and submit an Internshala application using a pre-existing driver.
    """
    try:
        if listing.get("source") != "internshala":
            return {"success": False, "message": "Not an Internshala listing"}

        if os.getenv("DRY_RUN", "false").lower() == "true":
            logger.info(f"  [DRY RUN] Would apply to {listing.get('title')} @ {listing.get('company')}")
            return {"success": True, "message": "Dry run — not submitted"}

        # Navigate to the internship page
        apply_url = listing.get("apply_url", "")
        logger.info(f"[Internshala] Navigating to: {apply_url}")
        driver.get(apply_url)
        time.sleep(random.uniform(2.0, 4.0))

        # Check for 404 or invalid page
        if "404" in driver.title.lower() or "not found" in driver.page_source.lower():
            return {"success": False, "message": "Listing page not found (404)"}

        # Step 3: Click "Apply Now" button
        apply_clicked = False
        apply_selectors = [
            "button#continue_button",
            "a.btn.btn-primary.apply_button",
            "button.apply_button",
            "#apply_button",
            "a[id*='apply']",
            "button[id*='apply']",
            "a.apply_now_btn",
            ".apply_now_button",
        ]

        for selector in apply_selectors:
            try:
                btn = driver.find_element("css selector", selector)
                if btn.is_displayed():
                    btn.click()
                    apply_clicked = True
                    logger.info("  ✓ Clicked Apply Now button")
                    time.sleep(random.uniform(2.0, 3.0))
                    break
            except Exception:
                continue

        if not apply_clicked:
            # Try by link text as fallback
            try:
                from selenium.webdriver.common.by import By

                btn = driver.find_element(By.PARTIAL_LINK_TEXT, "Apply")
                btn.click()
                apply_clicked = True
                time.sleep(random.uniform(2.0, 3.0))
            except Exception:
                pass

        if not apply_clicked:
            logger.warning("[SeleniumFill] Could not find Apply button")
            _take_screenshot(driver, "no_apply_button")
            return {"success": False, "message": "Could not find Apply Now button"}

        # Step 4: Fill cover letter textarea
        cover_filled = False
        textarea_selectors = [
            "textarea#cover_letter",
            "textarea[name='cover_letter']",
            "textarea.cover_letter",
            "textarea#text_input",
            "textarea[placeholder*='cover']",
            "textarea[placeholder*='Cover']",
            "textarea[placeholder*='answer']",
            ".ql-editor",  # Quill rich text editor
        ]

        for selector in textarea_selectors:
            try:
                textarea = driver.find_element("css selector", selector)
                if textarea.is_displayed():
                    textarea.clear()
                    # Type the cover note character by character for natural behavior
                    # (but send_keys in chunks for speed)
                    textarea.send_keys(cover_note)
                    cover_filled = True
                    logger.info("  ✓ Filled cover letter textarea")
                    time.sleep(random.uniform(1.0, 2.0))
                    break
            except Exception:
                continue

        # If there are any additional text inputs (e.g., availability questions)
        try:
            extra_textareas = driver.find_elements("css selector", "textarea:not([id='cover_letter'])")
            for ta in extra_textareas:
                if ta.is_displayed() and not ta.get_attribute("value"):
                    ta.send_keys("Yes, I am available to start immediately.")
        except Exception:
            pass

        if not cover_filled:
            logger.warning("[SeleniumFill] Could not find cover letter field")
            _take_screenshot(driver, "no_cover_field")
            # Don't fail — some applications don't have a cover letter field

        # Step 5: Submit the application
        submit_clicked = False
        submit_selectors = [
            "button#submit",
            "button[type='submit']",
            "input[type='submit']",
            "button.submit_button",
            "#submit_button",
            "button.btn-primary[type='submit']",
        ]

        for selector in submit_selectors:
            try:
                btn = driver.find_element("css selector", selector)
                if btn.is_displayed() and btn.is_enabled():
                    btn.click()
                    submit_clicked = True
                    logger.info("  ✓ Clicked Submit button")
                    time.sleep(random.uniform(3.0, 5.0))
                    break
            except Exception:
                continue

        if not submit_clicked:
            logger.warning("[SeleniumFill] Could not find Submit button")
            _take_screenshot(driver, "no_submit_button")
            return {"success": False, "message": "Could not find Submit button"}

        # Step 6: Check for success confirmation
        page_source = driver.page_source.lower()
        if (
            "successfully" in page_source
            or "application submitted" in page_source
            or "applied" in page_source
            or "thank you" in page_source
        ):
            logger.info(
                f"[Internshala] ✅ Successfully applied to "
                f"{listing.get('title')} at {listing.get('company')}"
            )
            return {"success": True, "message": "Application submitted successfully"}

        _take_screenshot(driver, "submit_uncertain")
        return {
            "success": True,
            "message": "Submit clicked but confirmation uncertain — check manually",
        }

    except Exception as e:
        logger.error(f"[Internshala] ✗ Error during application: {e}")
        _take_screenshot(driver, "application_error")
        return {"success": False, "message": f"Error: {str(e)}"}
