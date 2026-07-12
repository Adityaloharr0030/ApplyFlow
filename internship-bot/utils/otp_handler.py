"""
utils/otp_handler.py
────────────────────
OTP Pause & Resume handler.

Like ApplyCove: "Pauses for OTP so it never bypasses your security.
You watch every action live in the dashboard and can pause or take over at any point."

Detects OTP input screens, notifies the user, and waits for them to enter the OTP.
"""

import logging
import time

logger = logging.getLogger(__name__)

# Common OTP indicators across Indian job platforms
OTP_INDICATORS = [
    "otp",
    "one time password",
    "verification code",
    "enter the code",
    "we sent a code",
    "verify your",
    "enter otp",
    "otp sent",
    "mobile verification",
    "email verification",
    "verify otp",
]

OTP_INPUT_SELECTORS = [
    "input[name*='otp']",
    "input[placeholder*='OTP']",
    "input[placeholder*='otp']",
    "input[placeholder*='code']",
    "input[placeholder*='verification']",
    "input[type='tel'][maxlength='6']",
    "input[type='tel'][maxlength='4']",
    "input[type='number'][maxlength='6']",
    "input[type='number'][maxlength='4']",
    "input.otp-input",
    "input[id*='otp']",
    "input[autocomplete='one-time-code']",
]


def detect_otp_screen(driver) -> bool:
    """
    Check if the current page is showing an OTP/verification input screen.
    Returns True if OTP input is detected.
    """
    try:
        page_source = driver.page_source.lower()

        # Check page text for OTP indicators
        has_otp_text = any(indicator in page_source for indicator in OTP_INDICATORS)

        if not has_otp_text:
            return False

        # Confirm by looking for OTP input fields
        for selector in OTP_INPUT_SELECTORS:
            try:
                elements = driver.find_elements("css selector", selector)
                for el in elements:
                    if el.is_displayed():
                        logger.info("[OTP] Detected OTP input field on page")
                        return True
            except Exception:
                continue

        # Check for multiple single-digit inputs (common OTP UI pattern)
        try:
            single_inputs = driver.find_elements(
                "css selector",
                "input[maxlength='1'][type='tel'], input[maxlength='1'][type='text'], input[maxlength='1'][type='number']"
            )
            visible_singles = [el for el in single_inputs if el.is_displayed()]
            if len(visible_singles) >= 4:
                logger.info(f"[OTP] Detected {len(visible_singles)} single-digit OTP inputs")
                return True
        except Exception:
            pass

        return False

    except Exception as e:
        logger.debug(f"[OTP] Error detecting OTP screen: {e}")
        return False


def _send_otp_notification(platform: str):
    """Send notification to user that OTP is required."""
    msg = (
        f"⏸ OTP Required on {platform}!\n"
        f"The bot has paused and is waiting for you to enter the OTP.\n"
        f"Please check your phone/email and enter the OTP in the browser.\n"
        f"The bot will automatically resume once the OTP page advances."
    )

    # Try Telegram
    try:
        from notifier.telegram import send_instant as telegram_instant
        telegram_instant(msg)
    except Exception as e:
        logger.debug(f"[OTP] Telegram notification failed: {e}")

    # Try ntfy
    try:
        from notifier.push import send_instant as ntfy_instant
        ntfy_instant(msg, tags="warning")
    except Exception as e:
        logger.debug(f"[OTP] Ntfy notification failed: {e}")

    # Try WhatsApp
    try:
        from notifier.whatsapp import send_instant as whatsapp_instant
        whatsapp_instant(msg)
    except Exception as e:
        logger.debug(f"[OTP] WhatsApp notification failed: {e}")


def wait_for_otp(driver, platform: str = "Platform", timeout: int = 120) -> bool:
    """
    Wait for the user to enter the OTP and the page to advance.

    1. Sends notification to user via all configured channels
    2. Polls the page every 3 seconds
    3. Returns True if the page advances (OTP accepted), False on timeout

    Args:
        driver:   Selenium WebDriver instance
        platform: Platform name for the notification message
        timeout:  Max seconds to wait (default 120 = 2 minutes)

    Returns:
        True if OTP was entered and page advanced, False if timed out.
    """
    logger.warning(f"[OTP] ⏸ OTP required on {platform}! Pausing and notifying user...")

    # Send notifications
    _send_otp_notification(platform)

    # Record the current URL to detect page navigation
    initial_url = driver.current_url
    initial_page_hash = hash(driver.page_source[:500])

    elapsed = 0
    poll_interval = 3

    while elapsed < timeout:
        time.sleep(poll_interval)
        elapsed += poll_interval

        try:
            # Check if page URL changed (OTP accepted, redirected)
            current_url = driver.current_url
            if current_url != initial_url:
                logger.info(f"[OTP] ✅ Page navigated away from OTP screen! Resuming...")
                return True

            # Check if OTP inputs are no longer visible (form submitted)
            if not detect_otp_screen(driver):
                logger.info(f"[OTP] ✅ OTP screen no longer detected! Resuming...")
                return True

            # Check if page content changed significantly
            current_hash = hash(driver.page_source[:500])
            if current_hash != initial_page_hash:
                # Page changed but still same URL — check if OTP fields gone
                if not detect_otp_screen(driver):
                    logger.info(f"[OTP] ✅ Page content changed and OTP screen gone! Resuming...")
                    return True
                initial_page_hash = current_hash

            remaining = timeout - elapsed
            if remaining > 0 and elapsed % 30 == 0:
                logger.info(f"[OTP] Still waiting for OTP... {remaining}s remaining")

        except Exception as e:
            logger.debug(f"[OTP] Error during OTP wait: {e}")

    logger.error(f"[OTP] ✗ Timed out waiting for OTP ({timeout}s)")
    return False


def handle_otp_if_present(driver, platform: str = "Platform", timeout: int = 120) -> bool:
    """
    Convenience function: check for OTP and handle it if present.
    Returns True if no OTP was needed or if OTP was successfully handled.
    Returns False if OTP timed out.
    """
    if detect_otp_screen(driver):
        return wait_for_otp(driver, platform=platform, timeout=timeout)
    return True
