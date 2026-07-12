"""
platforms/unstop.py
───────────────────
Adapter for Unstop.
Uses the public JSON API for scraping, and Selenium for applying.
"""

import logging
import random
import time
import os
import requests
from typing import Any
from .base import Platform

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
}

class UnstopPlatform(Platform):
    def __init__(self):
        super().__init__()

    def search(self, profile: dict) -> list[dict]:
        if self.blocked:
            return []
            
        keyword = profile.get("keywords", ["internship"])[0]
        url = f"https://unstop.com/api/public/opportunity/search-result?opportunity=internships&keyword={keyword}&page=1"

        logger.info(f"[Unstop] Searching JSON API: keyword={keyword}")

        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            
            data = resp.json()
            items = data.get("data", {}).get("data", [])
            
            listings: list[dict] = []

            for item in items:
                title = item.get("title")
                company = item.get("organization", {}).get("name") or item.get("seo_url")
                seo_url = item.get("seo_url", "")
                if seo_url.startswith("http"):
                    apply_url = seo_url
                else:
                    apply_url = f"https://unstop.com/{seo_url}"
                
                if title and apply_url:
                    listings.append({
                        "title": title,
                        "company": company,
                        "location": item.get("location", "Not specified"),
                        "apply_url": apply_url,
                        "source": "unstop",
                    })

            logger.info(f"[Unstop] ✓ Found {len(listings)} listing(s)")
            return listings

        except Exception as e:
            logger.warning(f"[Unstop] ✗ Search failed: {e}")
            return []

    def apply(self, listing: dict, cover_note: str, profile: dict, driver: Any) -> dict:
        if self.blocked:
            return {"success": False, "message": "Platform blocked by circuit breaker"}

        try:
            if os.getenv("DRY_RUN", "false").lower() == "true":
                logger.info(f"  [DRY RUN] Would apply to {listing.get('title')} @ {listing.get('company')}")
                return {"success": True, "message": "Dry run — not submitted"}

            from utils.human_sim import human_click, human_scroll, random_idle, simulate_page_read
            from utils.otp_handler import handle_otp_if_present
            from agent.form_filler import fill_form_fields, answer_question

            apply_url = listing.get("apply_url", "")

            # ── Human-like warm-up ─────────────────────────────────────────
            try:
                driver.get("https://unstop.com/internships")
                random_idle(2.0, 4.0)
                human_scroll(driver, direction="down")
                random_idle(0.8, 1.5)
            except Exception:
                pass

            logger.info(f"[Unstop] Navigating to: {apply_url}")
            driver.get(apply_url)
            random_idle(3.0, 5.0)

            # ── Auth check ─────────────────────────────────────────────────
            if "login" in driver.current_url.lower() or "auth" in driver.current_url.lower():
                logger.warning("[Unstop] Not logged in — redirected to login/auth page")
                return {"success": False, "message": "Not logged in — login required"}

            # ── CAPTCHA detection ──────────────────────────────────────────
            if "captcha" in driver.page_source.lower() or "blocked" in driver.page_source.lower():
                if os.getenv("HEADLESS", "true").lower() == "false":
                    logger.warning("  ⚠️ Captcha detected! You have 60 seconds to solve it...")
                    for _ in range(20):
                        time.sleep(3)
                        if "captcha" not in driver.page_source.lower() and "blocked" not in driver.page_source.lower():
                            logger.info("  ✓ Captcha solved!")
                            break
                    else:
                        self.record_captcha()
                        return {"success": False, "message": "Blocked by CAPTCHA (Timeout)"}
                else:
                    self.record_captcha()
                    return {"success": False, "message": "Blocked by CAPTCHA"}

            # ── Simulate reading the listing page ──────────────────────────
            simulate_page_read(driver)

            # ── Find and click Apply button ────────────────────────────────
            apply_clicked = False
            apply_selectors = [
                "button.btn-apply",
                "a.btn-apply",
                "button[title='Apply']",
                "button.apply-btn",
                ".apply_btn button",
                "button.btn-primary.apply",
                "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'apply now')]",
                "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'apply')]",
                "//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'apply')]",
                "//div[contains(@class, 'apply')]//button",
            ]

            for selector in apply_selectors:
                try:
                    if selector.startswith("//"):
                        btn = driver.find_element("xpath", selector)
                    else:
                        btn = driver.find_element("css selector", selector)

                    if btn.is_displayed():
                        human_click(driver, btn)
                        apply_clicked = True
                        logger.info("  ✓ Clicked Apply button")
                        random_idle(2.0, 3.0)
                        break
                except Exception:
                    continue

            if not apply_clicked:
                return {"success": False, "message": "No Apply button found (Manual apply required)"}

            # ── Multi-step form loop ───────────────────────────────────────
            max_steps = 6
            for step in range(max_steps):
                random_idle(1.5, 3.0)

                try:
                    # ── Fill form fields at this step ──────────────────────
                    filled = fill_form_fields(driver, profile)
                    if filled > 0:
                        logger.info(f"  [Step {step+1}] Filled {filled} field(s)")

                    # ── Handle textareas ───────────────────────────────────
                    try:
                        textareas = driver.find_elements("css selector", "textarea")
                        for ta in textareas:
                            if ta.is_displayed() and not (ta.get_attribute("value") or "").strip():
                                from agent.form_filler import _get_field_label
                                label = _get_field_label(driver, ta)
                                if label:
                                    answer = answer_question(label, profile)
                                else:
                                    answer = cover_note[:500] if cover_note else "I am excited about this opportunity."
                                ta.send_keys(answer)
                                logger.info(f"  ✓ Filled textarea: {(label or 'additional')[:30]}")
                                random_idle(0.5, 1.0)
                    except Exception:
                        pass

                    # ── Handle resume upload ───────────────────────────────
                    try:
                        file_inputs = driver.find_elements("css selector", "input[type='file']")
                        resume_path = profile.get("resume_path", "")
                        if file_inputs and resume_path:
                            abs_path = os.path.abspath(resume_path)
                            if os.path.exists(abs_path):
                                for fi in file_inputs:
                                    try:
                                        fi.send_keys(abs_path)
                                        logger.info("  ✓ Uploaded resume")
                                        random_idle(1.0, 2.0)
                                        break
                                    except Exception:
                                        continue
                    except Exception:
                        pass

                    # ── Handle OTP ─────────────────────────────────────────
                    if not handle_otp_if_present(driver, platform="Unstop", timeout=120):
                        self.record_captcha()
                        return {"success": False, "message": "OTP verification timed out"}

                    # ── Check for error messages ───────────────────────────
                    try:
                        errors = driver.find_elements("css selector",
                            ".error-message, .form-error, [class*='error'], .invalid-feedback"
                        )
                        visible_errors = [e for e in errors if e.is_displayed() and e.text.strip()]
                        if visible_errors:
                            logger.warning(f"  ⚠️ Form errors: {[e.text for e in visible_errors[:3]]}")
                            fill_form_fields(driver, profile)
                            random_idle(0.5, 1.0)
                    except Exception:
                        pass

                    # ── Look for Submit / Next / Confirm buttons ───────────
                    submit_btn = None
                    next_btn = None

                    buttons = driver.find_elements("css selector", "button, input[type='submit']")
                    for btn in buttons:
                        if not btn.is_displayed() or not btn.is_enabled():
                            continue
                        text = (btn.text or btn.get_attribute("value") or "").lower().strip()
                        if "submit" in text or "confirm" in text or "register" in text:
                            submit_btn = btn
                        elif "next" in text or "continue" in text or "proceed" in text:
                            next_btn = btn

                    if submit_btn:
                        human_click(driver, submit_btn)
                        logger.info("  ✓ Clicked Submit/Confirm")
                        random_idle(3.0, 5.0)

                        # Post-submit OTP
                        if not handle_otp_if_present(driver, platform="Unstop", timeout=120):
                            return {"success": False, "message": "Post-submit OTP timed out"}

                        self.captcha_count = 0

                        # Verify
                        page_lower = driver.page_source.lower()
                        if any(kw in page_lower for kw in ["success", "submitted", "registered", "thank you", "applied", "congratulations"]):
                            return {"success": True, "message": "Unstop Application submitted successfully"}
                        return {"success": True, "message": "Unstop Application submitted (confirmation uncertain)"}

                    if next_btn:
                        human_click(driver, next_btn)
                        logger.info(f"  ✓ Clicked Next (Step {step+1})")
                        random_idle(1.5, 3.0)
                    else:
                        # Check if already submitted (1-click apply)
                        page_lower = driver.page_source.lower()
                        if any(kw in page_lower for kw in ["success", "submitted", "registered", "applied", "congratulations"]):
                            self.captcha_count = 0
                            return {"success": True, "message": "Unstop Application submitted (1-click)"}

                        # No buttons found - might be 1-click apply that just worked
                        if step == 0:
                            self.captcha_count = 0
                            return {"success": True, "message": "Unstop Application likely submitted (1-click)"}
                        break

                except Exception as e:
                    logger.debug(f"[Unstop] Step {step} failed: {e}")
                    continue

            return {"success": False, "message": "Form too complex (exceeded max steps)"}

        except Exception as e:
            logger.error(f"[Unstop] ✗ Error during application: {e}")
            return {"success": False, "message": f"Error: {str(e)}"}



