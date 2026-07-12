"""
platforms/linkedin.py
─────────────────────
Adapter for LinkedIn.
Uses the guest jobs API for scraping (no login needed), and Selenium for Easy Apply.
"""

import logging
import random
import time
import os
import requests
from bs4 import BeautifulSoup
from typing import Any
from .base import Platform

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

class LinkedInPlatform(Platform):
    def __init__(self):
        super().__init__()

    def search(self, profile: dict) -> list[dict]:
        if self.blocked:
            return []
            
        keywords = "+".join(profile.get("keywords", ["internship"])[:3])
        url = (
            f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
            f"?keywords={keywords}&location=India&f_WT=2&start=0"
        )

        logger.info(f"[LinkedIn] Searching guest API: keywords={keywords}")

        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")
            listings: list[dict] = []

            for card in soup.select("li"):
                title_el = card.select_one(".base-search-card__title")
                company_el = card.select_one(".base-search-card__subtitle")
                location_el = card.select_one(".job-search-card__location")
                link_el = card.select_one("a.base-card__full-link")

                if title_el and link_el:
                    listings.append({
                        "title": title_el.get_text(strip=True),
                        "company": company_el.get_text(strip=True) if company_el else "Unknown",
                        "location": location_el.get_text(strip=True) if location_el else "Not specified",
                        "apply_url": link_el["href"].split("?")[0],
                        "source": "linkedin",
                    })

                if len(listings) >= 15: # slightly bump up limit to find more
                    break

            logger.info(f"[LinkedIn] ✓ Found {len(listings)} listing(s)")
            return listings

        except Exception as e:
            logger.warning(f"[LinkedIn] ✗ Search failed: {e}")
            return []

    def apply(self, listing: dict, cover_note: str, profile: dict, driver) -> dict:
        if self.blocked:
            return {"success": False, "message": "Platform blocked by circuit breaker"}

        try:
            if os.getenv("DRY_RUN", "false").lower() == "true":
                logger.info(f"  [DRY RUN] Would apply to {listing.get('title')} @ {listing.get('company')}")
                return {"success": True, "message": "Dry run — not submitted"}

            from utils.human_sim import human_click, random_idle, simulate_page_read
            from agent.form_filler import fill_form_fields, answer_question

            apply_url = listing.get("apply_url", "")
            logger.info(f"[LinkedIn] Navigating to: {apply_url}")
            driver.get(apply_url)
            random_idle(3.0, 5.0)

            # Circuit breaker trigger for LinkedIn restricts
            if "login" in driver.current_url.lower() and "captcha" in driver.page_source.lower():
                self.record_captcha()
                return {"success": False, "message": "Hit CAPTCHA / Login wall"}

            # Check if redirected to login page (not authenticated)
            current_url = driver.current_url.lower()
            if "login" in current_url or "authwall" in current_url or "signup" in current_url:
                logger.warning("[LinkedIn] Not logged in — redirected to login/authwall")
                return {"success": False, "message": "Not logged in — login required"}

            # ── Find and click Easy Apply button ───────────────────────────
            easy_apply_clicked = False
            try:
                easy_apply_btn = driver.find_element("css selector", "button.jobs-apply-button")
                human_click(driver, easy_apply_btn)
                easy_apply_clicked = True
                logger.info("  ✓ Clicked Easy Apply button")
                random_idle(2.0, 3.0)
            except Exception:
                logger.warning("[LinkedIn] Could not find Easy Apply button. Trying text-based fallback...")

                # Fallback: search for visible elements containing "Easy Apply"
                try:
                    xpath = "//*[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'easy apply')]"
                    candidates = driver.find_elements("xpath", xpath)
                    for el in candidates:
                        try:
                            tag = el.tag_name.lower()
                            target = None
                            if tag in ("a", "button"):
                                target = el
                            else:
                                for ancestor_xpath in ["ancestor::button[1]", "ancestor::a[1]", "ancestor::*[@role='button'][1]"]:
                                    try:
                                        target = el.find_element("xpath", ancestor_xpath)
                                        break
                                    except Exception:
                                        continue

                            if target:
                                human_click(driver, target)
                                easy_apply_clicked = True
                                logger.info("  ✓ Clicked Easy Apply via fallback selector")
                                random_idle(2.0, 3.0)
                                break
                        except Exception:
                            continue
                except Exception:
                    pass

            if not easy_apply_clicked:
                return {"success": False, "message": "No Easy Apply button found (Manual apply required)"}

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
                            import os.path
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

                    # ── Handle textarea questions (cover letter, additional) ─
                    try:
                        textareas = driver.find_elements("css selector", "textarea")
                        for ta in textareas:
                            if ta.is_displayed() and not (ta.get_attribute("value") or "").strip():
                                from agent.form_filler import _get_field_label
                                label = _get_field_label(driver, ta)
                                if label:
                                    answer = answer_question(label, profile)
                                else:
                                    answer = cover_note[:500] if cover_note else "I am excited about this opportunity and believe my skills are a strong match."
                                ta.send_keys(answer)
                                logger.info(f"  ✓ Filled textarea: {(label or 'cover/additional')[:30]}")
                                random_idle(0.5, 1.0)
                    except Exception:
                        pass

                    # ── Check for error messages on this step ──────────────
                    try:
                        errors = driver.find_elements("css selector",
                            ".artdeco-inline-feedback--error, .fb-dash-form-element__error-field, "
                            "[data-test-form-element-error-text], .jobs-easy-apply-form-element__error"
                        )
                        visible_errors = [e for e in errors if e.is_displayed() and e.text.strip()]
                        if visible_errors:
                            logger.warning(f"  ⚠️ Form errors detected: {[e.text for e in visible_errors[:3]]}")
                            # Try filling again with AI for errored fields
                            fill_form_fields(driver, profile)
                            random_idle(0.5, 1.0)
                    except Exception:
                        pass

                    # ── Look for Submit / Review / Next buttons ─────────────
                    submit_btn = None
                    next_btn = None
                    review_btn = None

                    buttons = driver.find_elements("css selector", "button")
                    for btn in buttons:
                        if not btn.is_displayed() or not btn.is_enabled():
                            continue
                        text = btn.text.lower().strip()
                        if "submit application" in text:
                            submit_btn = btn
                        elif "review" in text:
                            review_btn = btn
                        elif "next" in text:
                            next_btn = btn

                    if submit_btn:
                        human_click(driver, submit_btn)
                        logger.info("  ✓ Clicked Submit Application")
                        random_idle(3.0, 5.0)
                        self.captcha_count = 0
                        return {"success": True, "message": "LinkedIn Application submitted successfully"}

                    if review_btn:
                        human_click(driver, review_btn)
                        logger.info("  ✓ Clicked Review")
                        random_idle(2.0, 4.0)

                        # After review, look for final submit
                        for btn in driver.find_elements("css selector", "button"):
                            if btn.is_displayed() and "submit application" in btn.text.lower():
                                human_click(driver, btn)
                                logger.info("  ✓ Clicked Final Submit")
                                random_idle(3.0, 5.0)
                                self.captcha_count = 0
                                return {"success": True, "message": "LinkedIn Application submitted successfully"}

                    if next_btn:
                        human_click(driver, next_btn)
                        logger.info(f"  ✓ Clicked Next (Step {step+1})")
                        random_idle(1.5, 3.0)
                    else:
                        if not submit_btn and not review_btn:
                            # Check for dismiss/close (application might have been submitted)
                            page_lower = driver.page_source.lower()
                            if "application sent" in page_lower or "applied" in page_lower:
                                self.captcha_count = 0
                                return {"success": True, "message": "LinkedIn Application submitted successfully"}
                            return {"success": False, "message": "Stuck on form (No Next or Submit found)"}

                except Exception as e:
                    logger.debug(f"[LinkedIn] Step {step} failed: {e}")
                    continue

            return {"success": False, "message": "Form too complex (exceeded max steps)"}

        except Exception as e:
            logger.error(f"[LinkedIn] ✗ Error during application: {e}")
            return {"success": False, "message": f"Error: {str(e)}"}
