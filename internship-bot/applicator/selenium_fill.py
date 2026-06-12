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
    Create an undetected Chrome WebDriver instance with a persistent profile.
    Returns None if Chrome/chromedriver aren't available.
    """
    try:
        import undetected_chromedriver as uc
        from pathlib import Path

        profile_dir = Path("./logs/chrome_profile").absolute()
        profile_dir.mkdir(parents=True, exist_ok=True)

        options = uc.ChromeOptions()
        options.add_argument(f"--user-data-dir={profile_dir}")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--window-size=1920,1080")
        # options.add_argument("--headless=new") # Headless breaks many CAPTCHAs

        driver = uc.Chrome(options=options, use_subprocess=True)
        driver.implicitly_wait(10)
        return driver
    except Exception as e:
        logger.error(f"[SeleniumFill] Failed to create Chrome driver: {e}")
        return None


def login_internshala(driver) -> bool:
    """
    Log into Internshala. Checks if already logged in first.
    Returns True on success.
    """
    try:
        logger.info("[Internshala] Checking login status...")
        driver.get("https://internshala.com/")
        time.sleep(random.uniform(2.0, 4.0))

        # If "Login" button is not present, we are likely already logged in
        page_source = driver.page_source.lower()
        if "logout" in page_source or "my applications" in page_source or "aditya" in page_source:
            logger.info("[Internshala] ✓ Already logged in (using saved session)")
            return True

        # Need to log in
        email = os.getenv("INTERNSHALA_EMAIL", "")
        password = os.getenv("INTERNSHALA_PASSWORD", "")

        if not email or not password:
            logger.warning("[Internshala] ✗ Credentials not set in .env")
            return False

        logger.info("[Internshala] Logging in…")
        driver.get("https://internshala.com/login")
        time.sleep(random.uniform(2.0, 3.5))

        email_field = driver.find_element("id", "email")
        email_field.clear()
        email_field.send_keys(email)
        time.sleep(random.uniform(0.3, 0.8))

        pass_field = driver.find_element("id", "password")
        pass_field.clear()
        pass_field.send_keys(password)
        time.sleep(random.uniform(0.3, 0.8))

        login_btn = driver.find_element(
            "css selector",
            "button#login_submit, button[type='submit']"
        )
        login_btn.click()
        time.sleep(random.uniform(3.0, 5.0))

        # Check for CAPTCHA
        page_source = driver.page_source.lower()
        if "captcha" in page_source or "recaptcha" in page_source:
            logger.warning("[Internshala] ⚠️ CAPTCHA detected! Pausing for 60 seconds so you can solve it manually in the Chrome window...")
            _take_screenshot(driver, "captcha_detected")
            time.sleep(60)
            
            if "login" not in driver.current_url.lower():
                logger.info("[Internshala] ✓ Manual CAPTCHA solve successful!")
                return True
            else:
                logger.warning("[Internshala] ✗ CAPTCHA not solved in time.")
                return False

        current_url = driver.current_url
        if "login" not in current_url.lower():
            logger.info("[Internshala] ✓ Login successful")
            return True

        logger.warning("[Internshala] ✗ Login might have failed — still on login page")
        _take_screenshot(driver, "login_uncertain")
        return False

    except Exception as e:
        logger.error(f"[Internshala] Login error: {e}")
        _take_screenshot(driver, "login_error")
        return False


def apply_internshala(driver, listing: dict, cover_note: str, profile: dict) -> dict:
    """
    Auto-fill and submit an Internshala application using a pre-existing driver.
    """
    try:
        if listing.get("source") != "internshala":
            return {"success": False, "message": "Not an Internshala listing"}

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
