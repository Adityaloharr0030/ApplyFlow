"""
platforms/login.py
──────────────────
Selenium-based login handlers for each platform.
Each function:
  - Checks if already logged in (via cookies/session in Chrome profile)
  - If not, performs automated login using credentials from .env
  - Returns True on success, False on failure
"""

import logging
import os
import time
import random

logger = logging.getLogger(__name__)

try:
    from utils.session_injector import load_session_into_driver
except ImportError:
    def load_session_into_driver(driver, platform):
        return False


def _save_debug_snapshot(driver, reason: str):
    try:
        from pathlib import Path
        from datetime import datetime
        
        debug_dir = Path("debug")
        debug_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%md_%H%M%S")
        prefix = f"{reason.replace(' ', '_')}_{timestamp}"
        
        screenshot_path = debug_dir / f"{prefix}.png"
        html_path = debug_dir / f"{prefix}.html"
        
        driver.save_screenshot(str(screenshot_path))
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(driver.page_source)
            
        visible_text = driver.find_element("tag name", "body").text
        snippet = visible_text[:200].replace("\n", " | ")
        
        logger.error(f"[Login Debug] Saved snapshot to debug/ ({reason})")
        logger.error(f"[Login Debug] URL: {driver.current_url}")
        logger.error(f"[Login Debug] Text snippet: {snippet}...")
    except Exception as e:
        logger.debug(f"[Login Debug] Failed to save snapshot: {e}")

def _wait_for_page_load(driver, timeout=10):
    try:
        from selenium.webdriver.support.ui import WebDriverWait
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
    except Exception:
        pass


def _wait_and_find(driver, css_selector, timeout=10, require_visible=True):
    """Wait for an element to appear and return it, or None."""
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    try:
        elements = WebDriverWait(driver, timeout).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, css_selector))
        )
        if require_visible:
            for element in elements:
                if element.is_displayed() and element.is_enabled():
                    return element
        return elements[0] if elements else None
    except Exception:
        return None


def _find_button_by_text(driver, texts, timeout=10):
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    try:
        buttons = WebDriverWait(driver, timeout).until(
            EC.presence_of_all_elements_located((By.TAG_NAME, "button"))
        )
        for btn in buttons:
            if not btn.is_displayed() or not btn.is_enabled():
                continue
            btn_text = (btn.text or "").strip().lower()
            if not btn_text:
                continue
            for text in texts:
                norm = text.strip().lower()
                if btn_text == norm:
                    return btn
            for text in texts:
                norm = text.strip().lower()
                if btn_text.startswith(norm):
                    remainder = btn_text[len(norm):].strip()
                    # Avoid matching "sign in" against "sign in with ..." unless the target text explicitly includes "with"
                    if remainder.startswith("with") and norm == text.strip().lower() and "with" not in norm:
                        continue
                    return btn
        return None
    except Exception:
        return None


def _is_logged_in_internshala(driver) -> bool:
    """Check if we're already logged into Internshala."""
    try:
        driver.get("https://internshala.com/")
        _wait_for_page_load(driver)
        time.sleep(random.uniform(0.5, 1.0))

        page_source = driver.page_source.lower()

        # If the page has a login/register button, we're NOT logged in
        # If it has profile/dashboard/logout links, we ARE logged in
        if "logout" in page_source or "my applications" in page_source:
            logger.info("[Login] ✓ Already logged into Internshala (session active)")
            return True

        # Check for guest indicator in page source
        if "is_guest = 1" in driver.page_source or "is_guest=1" in driver.page_source:
            return False

        # Check if login/register buttons are visible
        try:
            login_btn = driver.find_element("css selector",
                "a[href*='login'], button.login_btn, .login-cta, "
                "#login_link, a.nav_login_btn, a[href*='registration']"
            )
            if login_btn.is_displayed():
                return False
        except Exception:
            pass

        # If no clear indicator, assume not logged in
        return False
    except Exception as e:
        logger.debug(f"[Login] Error checking Internshala login status: {e}")
        return False


def login_internshala(driver) -> bool:
    """
    Log into Internshala using credentials from .env.
    Returns True if login succeeds or already logged in.
    """
    email = os.getenv("INTERNSHALA_EMAIL", "")
    password = os.getenv("INTERNSHALA_PASSWORD", "")

    if not email or not password:
        logger.warning("[Login] ✗ Internshala credentials not set in .env — cannot login")
        return False

    # Check if we have a captured session to inject first
    if load_session_into_driver(driver, "internshala"):
        if _is_logged_in_internshala(driver):
            logger.info("[Login] Using captured session for internshala")
            return True
        else:
            logger.warning("[Login] Captured session for internshala failed, falling back to credentials.")
            
    # Check if already logged in
    if _is_logged_in_internshala(driver):
        return True

    logger.info("[Login] Logging into Internshala...")

    try:
        # Navigate to login page
        driver.get("https://internshala.com/login")
        time.sleep(random.uniform(2.0, 4.0))

        # Handle cookie consent if present
        try:
            cookie_btn = driver.find_element("css selector",
                "button#cookie-accept, button.cookie-btn, [data-dismiss='cookie']"
            )
            if cookie_btn.is_displayed():
                cookie_btn.click()
                time.sleep(0.5)
        except Exception:
            pass

        # Fill email
        email_field = _wait_and_find(driver, "input#email, input[name='email'], input[type='email']")
        if not email_field:
            logger.error("[Login] ✗ Could not find email field on Internshala login page")
            return False

        email_field.clear()
        email_field.send_keys(email)
        time.sleep(random.uniform(0.5, 1.0))

        # Fill password
        password_field = _wait_and_find(driver, "input#password, input[name='password'], input[type='password']")
        if not password_field:
            logger.error("[Login] ✗ Could not find password field on Internshala login page")
            return False

        password_field.clear()
        password_field.send_keys(password)
        time.sleep(random.uniform(0.5, 1.0))

        # Click login button
        login_btn = None
        login_selectors = [
            "button#login_submit",
            "button[type='submit']",
            "input[type='submit']",
            "button.login_btn",
            "#login_submit_btn",
        ]
        for selector in login_selectors:
            try:
                btn = driver.find_element("css selector", selector)
                if btn.is_displayed() and btn.is_enabled():
                    login_btn = btn
                    break
            except Exception:
                continue

        if not login_btn:
            # Fallback: find by text
            try:
                from selenium.webdriver.common.by import By
                buttons = driver.find_elements(By.TAG_NAME, "button")
                for btn in buttons:
                    if "login" in btn.text.lower() or "sign in" in btn.text.lower():
                        login_btn = btn
                        break
            except Exception:
                pass

        if not login_btn:
            logger.error("[Login] ✗ Could not find Login button on Internshala")
            return False

        login_btn.click()
        time.sleep(random.uniform(3.0, 5.0))

        # Check for CAPTCHA
        page_source = driver.page_source.lower()
        if "captcha" in page_source or "unusual activity" in page_source:
            if os.getenv("HEADLESS", "true").lower() == "false":
                logger.warning("[Login] ⚠️ CAPTCHA detected during login! You have 60 seconds to solve it manually...")
                for _ in range(20):
                    time.sleep(3)
                    if "captcha" not in driver.page_source.lower() and "unusual activity" not in driver.page_source.lower():
                        logger.info("[Login] ✓ CAPTCHA solved!")
                        break
                else:
                    logger.error("[Login] ✗ CAPTCHA timeout — login failed")
                    _save_debug_snapshot(driver, "internshala_captcha_timeout")
                    return False
            else:
                logger.error("[Login] ✗ CAPTCHA detected in headless mode — login failed")
                _save_debug_snapshot(driver, "internshala_captcha_headless")
                return False

        # Check for error messages
        try:
            error_el = driver.find_element("css selector",
                ".error-message, .alert-danger, #error_message_container, .login-error"
            )
            if error_el.is_displayed() and error_el.text.strip():
                logger.error(f"[Login] ✗ Internshala login error: {error_el.text.strip()}")
                return False
        except Exception:
            pass

        # Verify login succeeded
        time.sleep(random.uniform(2.0, 3.0))
        page_source = driver.page_source.lower()
        current_url = driver.current_url.lower()

        if (
            "logout" in page_source
            or "my applications" in page_source
            or "dashboard" in current_url
            or "internshala.com/student" in current_url
            or "is_guest = 0" in driver.page_source
        ):
            logger.info("[Login] ✅ Successfully logged into Internshala!")
            return True

        # Check if still on login page (login may have failed silently)
        if "login" in current_url:
            logger.error("[Login] ✗ Still on login page — credentials may be wrong")
            _save_debug_snapshot(driver, "internshala_login_failed")
            return False

        # If we're redirected somewhere else, assume success
        logger.info("[Login] ✓ Internshala login likely succeeded (redirected away from login page)")
        return True

    except Exception as e:
        logger.error(f"[Login] ✗ Internshala login failed with exception: {e}")
        return False


def login_linkedin(driver) -> bool:
    """
    Log into LinkedIn.
    Returns True if already logged in (manual session) or if auto-login succeeds.
    """
    try:
        # Check if we have a captured session to inject first
        if load_session_into_driver(driver, "linkedin"):
            driver.get("https://www.linkedin.com/feed/")
            _wait_for_page_load(driver)
            time.sleep(random.uniform(0.5, 1.5))
            if "feed" in driver.current_url.lower() and "login" not in driver.current_url.lower():
                logger.info("[Login] Using captured session for linkedin")
                return True
            else:
                logger.warning("[Login] Captured session for linkedin failed, falling back to credentials.")

        # Check if already logged in FIRST
        driver.get("https://www.linkedin.com/feed/")
        _wait_for_page_load(driver)
        time.sleep(random.uniform(0.5, 1.5))

        if "feed" in driver.current_url.lower() and "login" not in driver.current_url.lower():
            logger.info("[Login] ✓ Already logged into LinkedIn (session active)")
            return True

        # If not logged in, try auto-login via .env
        email = os.getenv("LINKEDIN_EMAIL", "")
        password = os.getenv("LINKEDIN_PASSWORD", "")

        if not email or not password:
            logger.warning("[Login] ✗ LinkedIn credentials not set in .env and no active session found")
            return False

        logger.info("[Login] Logging into LinkedIn...")

        # Navigate to login page — try the direct login URL
        driver.get("https://www.linkedin.com/login")
        time.sleep(random.uniform(3.0, 5.0))

        # If redirected to authwall or checkpoint, go to login directly
        current_url = driver.current_url.lower()
        if "authwall" in current_url or "checkpoint" in current_url:
            driver.get("https://www.linkedin.com/uas/login")
            time.sleep(random.uniform(3.0, 5.0))

        # Fill email — try multiple selectors and only use visible inputs
        email_field = _wait_and_find(driver,
            "input[autocomplete='username'], input[autocomplete='username webauthn'], input[type='email'][autocomplete*='username']",
            timeout=15
        )
        if not email_field:
            # Last resort: try finding any visible email input
            try:
                from selenium.webdriver.common.by import By
                inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='email'], input[autocomplete*='username']")
                for inp in inputs:
                    if inp.is_displayed() and inp.is_enabled():
                        email_field = inp
                        break
            except Exception:
                pass

        if not email_field:
            logger.error("[Login] ✗ Could not find visible email field on LinkedIn login page")
            logger.debug(f"[Login] Current URL: {driver.current_url}")
            return False

        try:
            email_field.clear()
        except Exception:
            pass
        email_field.send_keys(email)
        time.sleep(random.uniform(0.5, 1.0))

        # Fill password — only use visible password field
        password_field = _wait_and_find(driver, "input[autocomplete='current-password'], input[type='password']", timeout=15)
        if not password_field:
            logger.error("[Login] ✗ Could not find visible password field on LinkedIn login page")
            return False

        try:
            password_field.clear()
        except Exception:
            pass
        password_field.send_keys(password)
        time.sleep(random.uniform(0.5, 1.0))

        # Click sign in — prefer the exact visible "Sign in" button and avoid federated sign-ins
        sign_in_btn = _find_button_by_text(driver, ["sign in"], timeout=10)
        if sign_in_btn:
            try:
                sign_in_btn.click()
            except Exception:
                driver.execute_script("arguments[0].click();", sign_in_btn)
        else:
            sign_in_btn = _wait_and_find(driver, "button[type='submit']", timeout=10)
            if sign_in_btn and sign_in_btn.is_displayed() and sign_in_btn.is_enabled():
                try:
                    sign_in_btn.click()
                except Exception:
                    driver.execute_script("arguments[0].click();", sign_in_btn)
            else:
                logger.error("[Login] ✗ Could not find Sign In button on LinkedIn")
                return False

        time.sleep(random.uniform(4.0, 6.0))

        # Check for security challenge / CAPTCHA
        current_url = driver.current_url.lower()
        if "checkpoint" in current_url or "challenge" in current_url:
            if os.getenv("HEADLESS", "true").lower() == "false":
                logger.warning("[Login] ⚠️ LinkedIn security challenge! You have 60 seconds to solve it manually...")
                for _ in range(20):
                    time.sleep(3)
                    if "feed" in driver.current_url.lower():
                        logger.info("[Login] ✓ Challenge solved!")
                        break
                else:
                    logger.error("[Login] ✗ LinkedIn challenge timeout")
                    _save_debug_snapshot(driver, "linkedin_challenge_timeout")
                    return False
            else:
                logger.error("[Login] ✗ LinkedIn security challenge in headless mode")
                _save_debug_snapshot(driver, "linkedin_challenge_headless")
                return False

        # Verify login
        if "feed" in driver.current_url.lower() or "mynetwork" in driver.current_url.lower():
            logger.info("[Login] ✅ Successfully logged into LinkedIn!")
            return True

        if "login" in driver.current_url.lower():
            logger.error("[Login] ✗ Still on login page — credentials may be wrong")
            _save_debug_snapshot(driver, "linkedin_login_failed")
            return False

        logger.info("[Login] ✓ LinkedIn login likely succeeded")
        return True

    except Exception as e:
        logger.error(f"[Login] ✗ LinkedIn login failed with exception: {e}")
        return False


def login_unstop(driver) -> bool:
    """
    Log into Unstop.
    """
    try:
        # Check if we have a captured session to inject first
        if load_session_into_driver(driver, "unstop"):
            driver.get("https://unstop.com/")
            _wait_for_page_load(driver)
            time.sleep(random.uniform(0.5, 1.0))
            if "login" not in driver.current_url.lower():
                logger.info("[Login] Using captured session for unstop")
                return True
            else:
                logger.warning("[Login] Captured session for unstop failed, falling back to credentials.")

        # Check if already logged in FIRST
        driver.get("https://unstop.com/")
        _wait_for_page_load(driver)
        time.sleep(random.uniform(0.5, 1.0))

        if "login" not in driver.current_url.lower():
            logger.info("[Login] ✓ Already logged into Unstop (session active)")
            return True

        # If not logged in, try auto-login via .env
        email = os.getenv("UNSTOP_EMAIL", "")
        password = os.getenv("UNSTOP_PASSWORD", "")

        if not email or not password:
            logger.warning("[Login] ✗ Unstop credentials not set in .env and no active session found")
            return False

        logger.info("[Login] Logging into Unstop...")

        # Navigate to login page
        driver.get("https://unstop.com/auth/login")
        time.sleep(random.uniform(2.0, 4.0))

        # Fill email
        email_field = _wait_and_find(driver, "input[type='email'], input[formcontrolname='email'], input[placeholder*='email' i]")
        if not email_field:
            logger.error("[Login] ✗ Could not find email field on Unstop login page")
            return False

        email_field.clear()
        email_field.send_keys(email)
        time.sleep(random.uniform(0.5, 1.0))

        # Fill password
        password_field = _wait_and_find(driver, "input[type='password'], input[formcontrolname='password']")
        if not password_field:
            logger.error("[Login] ✗ Could not find password field on Unstop login page")
            return False

        password_field.clear()
        password_field.send_keys(password)
        time.sleep(random.uniform(0.5, 1.0))

        # Click login button
        login_btn = _wait_and_find(driver, "button[type='submit'], button.login-btn, button.btn-login")
        if login_btn:
            login_btn.click()
        else:
            # Fallback: find by text
            try:
                from selenium.webdriver.common.by import By
                buttons = driver.find_elements(By.TAG_NAME, "button")
                for btn in buttons:
                    if "login" in btn.text.lower() or "sign in" in btn.text.lower():
                        btn.click()
                        break
                else:
                    logger.error("[Login] ✗ Could not find Login button on Unstop")
                    return False
            except Exception:
                logger.error("[Login] ✗ Could not find Login button on Unstop")
                return False

        time.sleep(random.uniform(4.0, 6.0))

        # Verify login
        page_source = driver.page_source.lower()
        current_url = driver.current_url.lower()
        if (
            "my profile" in page_source
            or "dashboard" in page_source
            or "logout" in page_source
            or "login" not in current_url
        ):
            logger.info("[Login] ✅ Successfully logged into Unstop!")
            return True

        logger.error("[Login] ✗ Unstop login may have failed")
        _save_debug_snapshot(driver, "unstop_login_failed")
        return False

    except Exception as e:
        logger.error(f"[Login] ✗ Unstop login failed with exception: {e}")
        return False


def login_naukri(driver) -> bool:
    """
    Log into Naukri.
    Returns True if already logged in (manual session) or if auto-login succeeds.
    """
    try:
        # Check if we have a captured session to inject first
        if load_session_into_driver(driver, "naukri"):
            driver.get("https://www.naukri.com/mnjuser/profile")
            _wait_for_page_load(driver)
            time.sleep(random.uniform(0.5, 1.5))
            current_url = driver.current_url.lower()
            if "profile" in current_url and "login" not in current_url and "nlogin" not in current_url:
                logger.info("[Login] Using captured session for naukri")
                return True
            else:
                logger.warning("[Login] Captured session for naukri failed, falling back to credentials.")

        # Check if already logged in FIRST
        driver.get("https://www.naukri.com/mnjuser/profile")
        _wait_for_page_load(driver)
        time.sleep(random.uniform(0.5, 1.5))

        current_url = driver.current_url.lower()
        # If we're on the profile page (not redirected to login), we're logged in
        if "profile" in current_url and "login" not in current_url and "nlogin" not in current_url:
            logger.info("[Login] ✓ Already logged into Naukri (session active)")
            return True

        # If not logged in, try auto-login via .env
        email = os.getenv("NAUKRI_EMAIL", "")
        password = os.getenv("NAUKRI_PASSWORD", "")

        if not email or not password:
            logger.warning("[Login] ✗ Naukri credentials not set in .env and no active session found")
            return False

        logger.info("[Login] Logging into Naukri...")

        # Navigate to login page
        driver.get("https://www.naukri.com/nlogin/login")
        time.sleep(random.uniform(3.0, 5.0))

        # Fill email
        email_field = _wait_and_find(driver,
            "input[type='text'][placeholder*='Email'], input[type='email'], input#usernameField",
            timeout=15
        )
        if not email_field:
            # Try finding any visible text input on the login page
            try:
                from selenium.webdriver.common.by import By
                inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='text'], input[type='email']")
                for inp in inputs:
                    if inp.is_displayed() and inp.is_enabled():
                        email_field = inp
                        break
            except Exception:
                pass

        if not email_field:
            logger.error("[Login] ✗ Could not find email field on Naukri login page")
            return False

        try:
            email_field.clear()
        except Exception:
            pass
        email_field.send_keys(email)
        time.sleep(random.uniform(0.5, 1.0))

        # Fill password
        password_field = _wait_and_find(driver,
            "input[type='password'], input#passwordField",
            timeout=10
        )
        if not password_field:
            logger.error("[Login] ✗ Could not find password field on Naukri login page")
            return False

        try:
            password_field.clear()
        except Exception:
            pass
        password_field.send_keys(password)
        time.sleep(random.uniform(0.5, 1.0))

        # Click login button
        login_btn = _find_button_by_text(driver, ["login", "sign in"], timeout=10)
        if not login_btn:
            login_btn = _wait_and_find(driver, "button[type='submit'], button.loginButton", timeout=10)

        if login_btn:
            try:
                login_btn.click()
            except Exception:
                driver.execute_script("arguments[0].click();", login_btn)
        else:
            logger.error("[Login] ✗ Could not find Login button on Naukri")
            return False

        time.sleep(random.uniform(4.0, 6.0))

        # Check for CAPTCHA
        page_source = driver.page_source.lower()
        if "captcha" in page_source or "unusual activity" in page_source:
            if os.getenv("HEADLESS", "true").lower() == "false":
                logger.warning("[Login] ⚠️ Naukri CAPTCHA detected! You have 60 seconds to solve it manually...")
                for _ in range(20):
                    time.sleep(3)
                    if "captcha" not in driver.page_source.lower() and "unusual" not in driver.page_source.lower():
                        logger.info("[Login] ✓ CAPTCHA solved!")
                        break
                else:
                    logger.error("[Login] ✗ CAPTCHA timeout — login failed")
                    _save_debug_snapshot(driver, "naukri_captcha_timeout")
                    return False
            else:
                logger.error("[Login] ✗ CAPTCHA detected in headless mode — login failed")
                _save_debug_snapshot(driver, "naukri_captcha_headless")
                return False

        # Check for OTP verification
        try:
            from utils.otp_handler import handle_otp_if_present
            if not handle_otp_if_present(driver, platform="Naukri", timeout=120):
                logger.error("[Login] ✗ OTP verification timed out")
                return False
        except ImportError:
            pass

        # Check for error messages
        try:
            error_el = driver.find_element("css selector",
                ".error-message, .alert-danger, .server-error, .login-error, .errMsg"
            )
            if error_el.is_displayed() and error_el.text.strip():
                logger.error(f"[Login] ✗ Naukri login error: {error_el.text.strip()}")
                return False
        except Exception:
            pass

        # Verify login succeeded
        time.sleep(random.uniform(2.0, 3.0))
        current_url = driver.current_url.lower()
        page_source = driver.page_source.lower()

        if (
            "nlogin" not in current_url
            or "profile" in current_url
            or "dashboard" in current_url
            or "logout" in page_source
            or "my profile" in page_source
        ):
            logger.info("[Login] ✅ Successfully logged into Naukri!")
            return True

        if "login" in current_url or "nlogin" in current_url:
            logger.error("[Login] ✗ Still on Naukri login page — credentials may be wrong")
            _save_debug_snapshot(driver, "naukri_login_failed")
            return False

        logger.info("[Login] ✓ Naukri login likely succeeded (redirected away from login page)")
        return True

    except Exception as e:
        logger.error(f"[Login] ✗ Naukri login failed with exception: {e}")
        return False


# Registry: maps platform source name → login function
LOGIN_HANDLERS = {
    "internshala": login_internshala,
    "linkedin": login_linkedin,
    "unstop": login_unstop,
    "naukri": login_naukri,
    # indeed and generic_web don't need login
}
