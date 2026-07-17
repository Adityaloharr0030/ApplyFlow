"""
utils/retry.py
──────────────
Retry decorators and DOM helpers for robust Selenium interactions.

Uses `tenacity` for exponential back-off on transient failures:
  - StaleElementReferenceException (DOM mutated before click)
  - ElementNotInteractableException (element covered/hidden)
  - TimeoutException (page too slow)

Usage:
    from utils.retry import safe_find, safe_click, wait_for

    btn = safe_find(driver, "button.apply")
    safe_click(driver, btn)
"""

import logging
import time
import random

from selenium.common.exceptions import (
    StaleElementReferenceException,
    ElementNotInteractableException,
    ElementClickInterceptedException,
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

logger = logging.getLogger(__name__)

# ── Transient exceptions worth retrying ────────────────────────────────────────
TRANSIENT_EXCEPTIONS = (
    StaleElementReferenceException,
    ElementNotInteractableException,
    ElementClickInterceptedException,
)


# ── Retry decorator for DOM clicks ─────────────────────────────────────────────

def dom_retry(max_attempts: int = 3, wait_min: float = 0.5, wait_max: float = 2.0):
    """
    Decorator: retry a DOM interaction on transient Selenium exceptions.
    Uses exponential back-off between attempts.

    Example:
        @dom_retry()
        def click_apply(driver, element):
            element.click()
    """
    return retry(
        reraise=True,
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=wait_min, max=wait_max),
        retry=retry_if_exception_type(TRANSIENT_EXCEPTIONS),
        before_sleep=before_sleep_log(logger, logging.DEBUG),
    )


# ── Safe DOM helpers ───────────────────────────────────────────────────────────

def safe_find(driver, selector: str, by: str = "css selector", timeout: float = 10.0):
    """
    Wait for an element to be present and visible, then return it.
    Returns None instead of raising if the element is never found.
    """
    try:
        by_map = {
            "css selector": "css selector",
            "css": "css selector",
            "xpath": "xpath",
            "id": "id",
            "name": "name",
            "class name": "class name",
            "tag name": "tag name",
        }
        actual_by = by_map.get(by.lower(), by)
        return WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located((actual_by, selector))
        )
    except TimeoutException:
        return None
    except Exception as e:
        logger.debug(f"[DOM] safe_find({selector!r}) failed: {e}")
        return None


def safe_find_all(driver, selector: str, by: str = "css selector", timeout: float = 5.0):
    """
    Wait briefly then return all matching elements.
    Returns empty list instead of raising.
    """
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, selector))
        )
        return driver.find_elements(by, selector)
    except TimeoutException:
        return []
    except Exception:
        return []


def safe_click(driver, element, fallback_js: bool = True) -> bool:
    """
    Click an element with 3 retry attempts on transient failures.
    Falls back to JS click if all Selenium clicks fail.
    Returns True if click succeeded.
    """
    @dom_retry(max_attempts=3)
    def _attempt(el):
        el.click()

    try:
        _attempt(element)
        return True
    except TRANSIENT_EXCEPTIONS as e:
        logger.debug(f"[DOM] Selenium click failed after retries: {e}")
        if fallback_js:
            try:
                driver.execute_script("arguments[0].click();", element)
                return True
            except Exception as js_e:
                logger.warning(f"[DOM] JS fallback click also failed: {js_e}")
    except Exception as e:
        logger.warning(f"[DOM] safe_click unexpected error: {e}")
    return False


def safe_send_keys(element, text: str) -> bool:
    """
    Send keys to an element, retrying on StaleElement.
    Returns True if successful.
    """
    @dom_retry(max_attempts=3)
    def _attempt(el, t):
        el.clear()
        el.send_keys(t)

    try:
        _attempt(element, text)
        return True
    except Exception as e:
        logger.debug(f"[DOM] safe_send_keys failed: {e}")
        return False


def wait_for(driver, selector: str, by: str = "css selector", timeout: float = 15.0):
    """
    Wait up to `timeout` seconds for an element to be clickable.
    Returns the element or None.
    """
    try:
        return WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((by, selector))
        )
    except TimeoutException:
        return None
    except Exception:
        return None


def wait_for_page_load(driver, timeout: float = 15.0):
    """Wait until document.readyState == 'complete'."""
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
    except TimeoutException:
        logger.debug("[DOM] Page load timed out — continuing anyway")


def find_button_by_text(driver, *texts: str, timeout: float = 5.0):
    """
    Find a visible, enabled button whose text matches any of the given strings (case-insensitive).
    Returns the first matching element or None.
    """
    time.sleep(min(timeout * 0.3, 1.5))  # Brief wait for DOM to settle
    try:
        all_btns = driver.find_elements("css selector", "button, input[type='submit'], a[role='button']")
        for btn in all_btns:
            try:
                if not btn.is_displayed() or not btn.is_enabled():
                    continue
                btn_text = (btn.text or btn.get_attribute("value") or "").lower().strip()
                if any(t.lower() in btn_text for t in texts):
                    return btn
            except StaleElementReferenceException:
                continue
    except Exception as e:
        logger.debug(f"[DOM] find_button_by_text failed: {e}")
    return None
