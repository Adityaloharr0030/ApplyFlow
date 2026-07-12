"""
applicator/selenium_fill.py  — REWRITTEN (Deep Fix Version)
Fixes:
  - Silent success bug (was returning success=True even when nothing happened)
  - Wrong Apply button selectors (now uses XPath + text-based detection)
  - Missing modal detection (Internshala opens application in a modal, not new page)
  - Screenshot at every step for debugging
  - Explicit WebDriverWait instead of time.sleep
"""

import logging
import os
import time
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)
SCREENSHOT_DIR = Path("./logs/screenshots")


def _save_screenshot(driver, label: str) -> Path:
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%H%M%S")
    path = SCREENSHOT_DIR / f"{ts}_{label}.png"
    try:
        driver.save_screenshot(str(path))
        logger.info(f"  📸 Screenshot: {path.name}")
    except Exception as e:
        logger.warning(f"  Screenshot failed: {e}")
    return path


def _wait_for(driver, css_selector: str, timeout: int = 10):
    """Wait for a CSS-selected element to be clickable. Returns element or None."""
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    try:
        return WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, css_selector))
        )
    except Exception:
        return None


def _wait_for_any(driver, selectors: list, timeout: int = 10):
    """Try multiple CSS selectors. Returns (selector, element) for first match."""
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    per = max(1, timeout // max(len(selectors), 1))
    for sel in selectors:
        try:
            el = WebDriverWait(driver, per).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, sel))
            )
            return sel, el
        except Exception:
            continue
    return None, None


def _wait_for_xpath(driver, xpath: str, timeout: int = 5):
    """Wait for an XPath element to be clickable. Returns element or None."""
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    try:
        return WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.XPATH, xpath))
        )
    except Exception:
        return None


def _login_internshala(driver) -> bool:
    email = os.getenv("INTERNSHALA_EMAIL", "")
    password = os.getenv("INTERNSHALA_PASSWORD", "")
    if not email or not password:
        logger.error("[Selenium] INTERNSHALA_EMAIL / INTERNSHALA_PASSWORD not set in .env")
        return False

    logger.info("[Selenium] Step 1/6 — Logging in to Internshala")
    driver.get("https://internshala.com/login/user")
    time.sleep(3)
    _save_screenshot(driver, "1_login_page")

    # Check if already logged in
    if "dashboard" in driver.current_url or "student" in driver.current_url:
        logger.info("  Already logged in (session active)")
        return True

    # Fill email
    email_field = _wait_for(driver, "#email, input[name='email'], input[type='email']")
    if not email_field:
        _save_screenshot(driver, "1_FAIL_no_email_field")
        logger.error("  Cannot find email field — screenshot saved")
        return False
    email_field.clear()
    email_field.send_keys(email)
    time.sleep(0.5)

    # Fill password
    pass_field = _wait_for(driver, "#password, input[name='password'], input[type='password']")
    if not pass_field:
        _save_screenshot(driver, "1_FAIL_no_password_field")
        logger.error("  Cannot find password field — screenshot saved")
        return False
    pass_field.clear()
    pass_field.send_keys(password)
    time.sleep(0.5)

    # Click login button
    login_btn = _wait_for(driver, "button#login_submit, button[type='submit'], .login-btn, button.btn-primary")
    if not login_btn:
        _save_screenshot(driver, "1_FAIL_no_login_button")
        logger.error("  Cannot find login button — screenshot saved")
        return False
    login_btn.click()
    time.sleep(4)
    _save_screenshot(driver, "1_after_login")

    # Check for CAPTCHA
    if "captcha" in driver.page_source.lower():
        logger.warning("  ⚠️ CAPTCHA detected! Please solve it manually in the browser window.")
        logger.warning("  Waiting up to 90 seconds for you to solve it...")
        
        # Wait for the user to solve the Captcha and login
        solved = False
        for i in range(90):
            if "login" not in driver.current_url.lower():
                solved = True
                break
            time.sleep(1)
            
        if not solved:
            logger.error("  Timed out waiting for CAPTCHA to be solved.")
            _save_screenshot(driver, "1_FAIL_captcha_timeout")
            return False
        else:
            logger.info("  ✅ CAPTCHA solved by user!")

    # Confirm we left the login page
    if "login" in driver.current_url.lower():
        logger.error("  Login failed — still on login page — wrong credentials?")
        _save_screenshot(driver, "1_FAIL_still_on_login")
        return False

    logger.info("  ✅ Logged in successfully")
    return True


def apply_internshala(listing: dict, cover_note: str, profile: dict) -> dict:
    """
    Apply to an Internshala listing via Selenium.
    Takes screenshots at every step — check logs/screenshots/ to debug failures.
    """
    if listing.get("source") != "internshala":
        return {"success": False, "message": "Not an Internshala listing"}

    apply_url = listing.get("apply_url", "")
    if not apply_url:
        return {"success": False, "message": "No apply_url in listing"}

    # Reuse the shared bot Chrome profile so the Internshala session is
    # preserved between runs — CAPTCHA only needs to be solved once.
    BOT_PROFILE = r"C:\ApplyFlow\bot_chrome_profile"
    
    if sys.platform == "win32":
        os.system("taskkill /F /IM chrome.exe /T >nul 2>&1")
        os.system("taskkill /F /IM undetected_chromedriver.exe /T >nul 2>&1")
        
        # Fix WinError 183 by removing the old executable if it exists
        uc_exe = os.path.join(os.getenv("APPDATA", ""), "undetected_chromedriver", "undetected_chromedriver.exe")
        if os.path.exists(uc_exe):
            try:
                os.remove(uc_exe)
            except Exception:
                pass
        
    try:
        import undetected_chromedriver as uc
        options = uc.ChromeOptions()
        options.add_argument(f"--user-data-dir={BOT_PROFILE}")
        options.add_argument("--profile-directory=Default")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--window-size=1366,768")
        if os.getenv("HEADLESS", "false").lower() == "true":
            options.add_argument("--headless=new")
        driver = uc.Chrome(options=options, use_subprocess=True)
        driver.set_page_load_timeout(30)
    except Exception as e:
        logger.error(f"[Selenium] Driver creation failed: {e}")
        return {"success": False, "message": f"Chrome driver creation failed: {e}"}

    try:
        # ── STEP 1: Login ──────────────────────────────────────────────────
        if not _login_internshala(driver):
            return {"success": False, "message": "Login failed — check credentials and screenshots in logs/screenshots/"}

        # ── STEP 2: Navigate to listing ───────────────────────────────────
        logger.info(f"[Selenium] Step 2/6 — Navigating to: {apply_url}")
        driver.get(apply_url)
        time.sleep(3)
        _save_screenshot(driver, "2_listing_page")

        # ── STEP 3: Find and click Apply button ───────────────────────────
        logger.info("[Selenium] Step 3/6 — Looking for Apply button")

        # CSS selectors for the Internshala Apply Now button (July 2026)
        apply_selectors = [
            "#continue_button",
            "button.btn-primary[data-bs-toggle]",
            "a.apply_now_btn",
            "button[class*='apply']",
            "a[class*='apply']",
            "#apply_button",
            ".apply-now-button",
            "button.apply_button",
        ]

        matched_sel, apply_btn = _wait_for_any(driver, apply_selectors, timeout=8)

        # XPath fallback — matches button text directly
        if not apply_btn:
            xpath_options = [
                "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'apply now')]",
                "//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'apply now')]",
                "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'apply')]",
            ]
            for xpath in xpath_options:
                el = _wait_for_xpath(driver, xpath, timeout=3)
                if el:
                    apply_btn = el
                    matched_sel = xpath
                    break

        if not apply_btn:
            page_lower = driver.page_source.lower()

            if "already applied" in page_lower or "withdraw application" in page_lower:
                _save_screenshot(driver, "3_already_applied")
                return {"success": False, "message": "Already applied to this listing"}

            if "login" in page_lower and "apply" in page_lower:
                _save_screenshot(driver, "3_FAIL_login_wall")
                return {"success": False, "message": "Login wall detected — session may have expired"}

            _save_screenshot(driver, "3_FAIL_no_apply_button")
            return {
                "success": False,
                "message": (
                    "Apply button not found — Internshala may have changed their HTML. "
                    "Check screenshot 3_FAIL_no_apply_button.png and update selectors. "
                    f"URL: {apply_url}"
                )
            }

        logger.info(f"  Found Apply button via: {matched_sel}")
        driver.execute_script("arguments[0].scrollIntoView(true);", apply_btn)
        time.sleep(0.5)
        apply_btn.click()
        time.sleep(3)
        _save_screenshot(driver, "3_after_apply_click")
        logger.info("  ✅ Clicked Apply button")

        # ── STEP 4: Fill cover letter / application form ───────────────────
        logger.info("[Selenium] Step 4/6 — Waiting for application form")

        # Internshala opens a modal with a cover letter textarea
        cover_selectors = [
            "textarea#cover_letter",
            "textarea[name='cover_letter']",
            "textarea[placeholder*='cover']",
            "textarea[placeholder*='Cover']",
            "textarea[placeholder*='answer']",
            "textarea[placeholder*='Answer']",
            ".ql-editor[contenteditable='true']",
            "textarea",
        ]

        matched_cover, cover_field = _wait_for_any(driver, cover_selectors, timeout=10)

        if cover_field:
            logger.info(f"  Found cover letter field via: {matched_cover}")
            try:
                cover_field.clear()
            except Exception:
                pass

            if "contenteditable" in matched_cover:
                # Rich text editor (Quill) — use JavaScript
                driver.execute_script("arguments[0].innerHTML = arguments[1];", cover_field, cover_note)
            else:
                cover_field.send_keys(cover_note)

            time.sleep(1)
            _save_screenshot(driver, "4_cover_filled")
            logger.info("  ✅ Cover letter filled")
        else:
            _save_screenshot(driver, "4_no_cover_field")
            logger.warning("  No cover letter textarea found — some listings skip this step")

        # Fill any extra textarea questions (availability, start date etc.)
        try:
            from selenium.webdriver.common.by import By
            extras = driver.find_elements(By.CSS_SELECTOR, "textarea:not(#cover_letter)")
            for ta in extras:
                if ta.is_displayed() and not ta.get_attribute("value"):
                    ta.send_keys("Yes, I am available to start immediately.")
        except Exception:
            pass

        # ── STEP 5: Submit the application ────────────────────────────────
        logger.info("[Selenium] Step 5/6 — Submitting application")

        submit_selectors = [
            "button#submit",
            "button[type='submit']",
            "input[type='submit']",
            "button.submit_button",
            "button[class*='submit']",
            "button.btn-primary[type='submit']",
        ]

        matched_sub, submit_btn = _wait_for_any(driver, submit_selectors, timeout=8)

        if not submit_btn:
            submit_btn = _wait_for_xpath(
                driver,
                "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'submit')]",
                timeout=5
            )

        if not submit_btn:
            _save_screenshot(driver, "5_FAIL_no_submit_button")
            return {
                "success": False,
                "message": "Submit button not found — check screenshot 5_FAIL_no_submit_button.png"
            }

        submit_btn.click()
        time.sleep(5)
        _save_screenshot(driver, "5_after_submit")
        logger.info("  ✅ Clicked Submit")

        # ── STEP 6: Verify actual success ─────────────────────────────────
        logger.info("[Selenium] Step 6/6 — Verifying submission")
        page = driver.page_source.lower()

        # Internshala's ACTUAL success confirmation strings — NOT generic words
        SUCCESS_STRINGS = [
            "your application has been submitted",
            "application submitted successfully",
            "you have successfully applied",
            "congratulations",
            "successfully submitted",
        ]

        actually_succeeded = any(s in page for s in SUCCESS_STRINGS)

        if actually_succeeded:
            _save_screenshot(driver, "6_SUCCESS")
            logger.info(f"  ✅ CONFIRMED application submitted to {listing.get('company')}")
            return {"success": True, "message": "Application submitted and confirmed by Internshala"}
        else:
            _save_screenshot(driver, "6_UNCERTAIN")
            # Do NOT return success=True — this was the original silent-success bug
            return {
                "success": False,
                "message": (
                    "Submit clicked but success page NOT detected. "
                    "Check screenshot 6_UNCERTAIN.png — the form may need additional fields. "
                    f"Apply manually: {apply_url}"
                )
            }

    except Exception as e:
        logger.error(f"[Selenium] Unexpected error: {e}")
        try:
            _save_screenshot(driver, "ERROR_unexpected")
        except Exception:
            pass
        return {"success": False, "message": f"Unexpected error: {e}"}

    finally:
        try:
            driver.quit()
        except Exception:
            pass
