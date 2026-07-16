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

            from utils.real_mouse import real_click, bring_browser_to_front
            from utils.human_sim import random_idle, simulate_page_read
            from utils.otp_handler import handle_otp_if_present
            from agent.form_filler import fill_form_fields, answer_question

            apply_url = listing.get("apply_url", "")
            logger.info(f"[Indeed] Navigating to: {apply_url}")
            driver.get(apply_url)
            random_idle(3.0, 5.0)

            # ── CAPTCHA / Cloudflare detection ─────────────────────────────
            if "captcha" in driver.page_source.lower() or "cloudflare" in driver.title.lower():
                if os.getenv("HEADLESS", "true").lower() == "false":
                    logger.warning("  ⚠️ Captcha detected! You have 60 seconds to solve it manually...")
                    for _ in range(20):
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

            # ── Click Indeed Apply button ──────────────────────────────────
            apply_clicked = False
            apply_selectors = [
                "#indeedApplyButton",
                "button[id*='indeedApply']",
                "button.indeed-apply-button",
                "button[data-indeed-apply-button]",
                "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'apply now')]",
                "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'apply')]",
            ]

            for selector in apply_selectors:
                try:
                    if selector.startswith("//"):
                        btn = driver.find_element("xpath", selector)
                    else:
                        btn = driver.find_element("css selector", selector)

                    if btn.is_displayed():
                        bring_browser_to_front(driver)
                        real_click(driver, btn)
                        apply_clicked = True
                        logger.info("  ✓ Clicked Indeed Apply button (real mouse)")
                        random_idle(2.0, 4.0)
                        break
                except Exception:
                    continue

            if not apply_clicked:
                logger.warning("[Indeed] External site or manual apply required.")
                return {"success": False, "message": "External ATS redirect (Manual apply required)"}

            # ── Switch to iframe if Indeed Apply modal opens ───────────────
            in_iframe = False
            try:
                iframe = driver.find_element("css selector", "iframe[title*='Indeed Apply'], iframe[id*='indeed-ia']")
                driver.switch_to.frame(iframe)
                in_iframe = True
                logger.info("  ✓ Switched to Indeed Apply iframe")
                random_idle(1.0, 2.0)
            except Exception:
                pass  # not an iframe, it's inline

            # ── Multi-step form loop with smart filling ────────────────────
            max_steps = 8
            for step in range(max_steps):
                random_idle(1.5, 3.0)

                try:
                    # ── Fill form fields at this step ──────────────────────
                    filled = fill_form_fields(driver, profile)
                    if filled > 0:
                        logger.info(f"  [Step {step+1}] Filled {filled} field(s)")

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

                    # ── Handle textareas (cover letter, additional Qs) ─────
                    try:
                        textareas = driver.find_elements("css selector", "textarea")
                        for ta in textareas:
                            if ta.is_displayed() and not (ta.get_attribute("value") or "").strip():
                                from agent.form_filler import _get_field_label
                                label = _get_field_label(driver, ta)
                                if label:
                                    answer = answer_question(label, profile)
                                else:
                                    answer = cover_note[:500] if cover_note else "I am eager to contribute and grow in this role."
                                ta.send_keys(answer)
                                logger.info(f"  ✓ Filled textarea: {(label or 'additional')[:30]}")
                                random_idle(0.5, 1.0)
                    except Exception:
                        pass

                    # ── Handle OTP if required ─────────────────────────────
                    if not handle_otp_if_present(driver, platform="Indeed", timeout=120):
                        self.record_captcha()
                        if in_iframe:
                            driver.switch_to.default_content()
                        return {"success": False, "message": "OTP verification timed out"}

                    # ── Check for error messages ───────────────────────────
                    try:
                        errors = driver.find_elements("css selector",
                            ".ia-BasePage-errorMessage, .ia-FormField-errorMessage, "
                            "[data-testid='error-message'], .css-1qd7bp7"
                        )
                        visible_errors = [e for e in errors if e.is_displayed() and e.text.strip()]
                        if visible_errors:
                            logger.warning(f"  ⚠️ Form errors: {[e.text for e in visible_errors[:3]]}")
                            fill_form_fields(driver, profile)
                            random_idle(0.5, 1.0)
                    except Exception:
                        pass

                    # ── Look for Submit / Continue buttons ─────────────────
                    submit_btn = None
                    continue_btn = None

                    buttons = driver.find_elements("css selector", "button")
                    for btn in buttons:
                        if not btn.is_displayed() or not btn.is_enabled():
                            continue
                        text = btn.text.lower().strip()
                        if "submit" in text or ("apply" in text and "indeed" not in text):
                            submit_btn = btn
                        elif "continue" in text or "next" in text:
                            continue_btn = btn

                    if submit_btn:
                        real_click(driver, submit_btn)
                        logger.info("  ✓ Clicked Submit/Apply (real mouse)")
                        random_idle(3.0, 5.0)
                        self.captcha_count = 0
                        if in_iframe:
                            driver.switch_to.default_content()

                        # Verify submission
                        page_lower = driver.page_source.lower()
                        if "application" in page_lower and ("sent" in page_lower or "submitted" in page_lower or "received" in page_lower):
                            return {"success": True, "message": "Indeed Application submitted successfully"}
                        return {"success": True, "message": "Indeed Application submitted (confirmation uncertain)"}

                    if continue_btn:
                        real_click(driver, continue_btn)
                        logger.info(f"  ✓ Clicked Continue (Step {step+1}) (real mouse)")
                        random_idle(1.5, 3.0)
                    else:
                        # Check if we've been submitted already
                        page_lower = driver.page_source.lower()
                        if "application" in page_lower and ("sent" in page_lower or "submitted" in page_lower):
                            self.captcha_count = 0
                            if in_iframe:
                                driver.switch_to.default_content()
                            return {"success": True, "message": "Indeed Application submitted successfully"}
                        break

                except Exception as e:
                    logger.debug(f"[Indeed] Step {step} failed: {e}")
                    continue

            if in_iframe:
                driver.switch_to.default_content()
            return {"success": False, "message": "Form too complex (exceeded max steps)"}

        except Exception as e:
            logger.error(f"[Indeed] ✗ Error during application: {e}")
            try:
                driver.switch_to.default_content()
            except Exception:
                pass
            return {"success": False, "message": f"Error: {str(e)}"}



