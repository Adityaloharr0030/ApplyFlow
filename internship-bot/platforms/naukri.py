"""
platforms/naukri.py
───────────────────
Adapter for Naukri (naukri.com) — India's #1 job portal.

Like ApplyCove: "ApplyCove handles Naukri's multi-step application flow
(including OTP verification with pause-and-resume), Naukri Recommended Jobs,
Naukri search results."

Supports:
  - Search: Scrapes Naukri job listings via their search pages
  - Apply: Selenium-based application with smart form filling
  - OTP Pause: Detects OTP screen, notifies user, waits for input
  - India fields: Notice period, CTC, relocation auto-filled from profile
"""

import logging
import random
import re
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
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-IN,en;q=0.9,hi;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.naukri.com/",
}

# Naukri API endpoint for job search
NAUKRI_API_URL = "https://www.naukri.com/jobapi/v3/search"

NAUKRI_API_HEADERS = {
    "User-Agent": HEADERS["User-Agent"],
    "Accept": "application/json",
    "Accept-Language": "en-IN,en;q=0.9",
    "appid": "109",
    "systemid": "Naukri",
    "Content-Type": "application/json",
}


class NaukriPlatform(Platform):
    def __init__(self):
        super().__init__()

    def _build_search_urls(self, profile: dict) -> list[str]:
        """Build Naukri search URLs from profile keywords."""
        urls = []
        keywords = profile.get("keywords", ["software developer"])

        for kw in keywords[:5]:  # Limit to 5 keyword searches
            slug = kw.strip().lower().replace(" ", "-")
            url = f"https://www.naukri.com/{slug}-jobs"
            urls.append(url)

        return urls

    def _scrape_html(self, url: str, session: requests.Session) -> list[dict]:
        """Scrape job listings from Naukri HTML pages."""
        listings = []
        try:
            logger.info(f"  ↳ Fetching: {url}")
            resp = session.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")

            # Naukri job cards — try multiple selectors
            cards = soup.select("article.jobTuple, div.srp-jobtuple-wrapper, div.cust-job-tuple, div[class*='jobTuple']")

            if not cards:
                # Fallback: look for job listing links
                cards = soup.select("a[href*='/job-listings-'], a.title")

            for card in cards:
                try:
                    # Title
                    title_el = card.select_one("a.title, .jobTitle a, h2 a, .row1 a.title, .info h2 a")
                    title = title_el.get_text(strip=True) if title_el else None

                    # Company
                    company_el = card.select_one("a.subTitle, .companyInfo a, .comp-name, .row2 .comp-name a")
                    company = company_el.get_text(strip=True) if company_el else "Unknown"

                    # Location
                    location_el = card.select_one(".locWdth, .loc, .location, .row3 .loc span, .ni-gnl .loc")
                    location = location_el.get_text(strip=True) if location_el else "Not specified"

                    # Experience
                    exp_el = card.select_one(".expwdth, .exp, .experience, .row3 .exp span")
                    experience = exp_el.get_text(strip=True) if exp_el else ""

                    # Salary
                    salary_el = card.select_one(".sal, .salary, .row3 .sal span")
                    salary = salary_el.get_text(strip=True) if salary_el else "Not disclosed"

                    # URL
                    link_el = title_el if title_el and title_el.name == "a" else card.select_one("a[href*='naukri.com']")
                    if link_el and link_el.get("href"):
                        href = link_el["href"]
                        apply_url = href if href.startswith("http") else f"https://www.naukri.com{href}"
                    else:
                        apply_url = None

                    # Description snippet
                    desc_el = card.select_one(".job-description, .ellipsis, .row4")
                    description = desc_el.get_text(strip=True) if desc_el else ""

                    if title and apply_url:
                        listings.append({
                            "title": title,
                            "company": company,
                            "location": location,
                            "experience": experience,
                            "stipend": salary,
                            "apply_url": apply_url,
                            "description": description,
                            "source": "naukri",
                        })

                except Exception as e:
                    logger.debug(f"  Failed to parse Naukri card: {e}")
                    continue

        except requests.exceptions.RequestException as e:
            logger.warning(f"  ✗ Network error scraping Naukri: {e}")
        except Exception as e:
            logger.warning(f"  ✗ Unexpected error scraping Naukri: {e}")

        return listings

    def _scrape_api(self, keyword: str) -> list[dict]:
        """Scrape job listings via Naukri's internal JSON API."""
        listings = []
        try:
            params = {
                "noOfResults": 20,
                "urlType": "search_by_keyword",
                "searchType": "adv",
                "keyword": keyword,
                "pageNo": 1,
                "experience": "0",
                "sort": "r",  # relevance
                "location": "",
            }

            logger.info(f"  ↳ Naukri API search: keyword={keyword}")
            resp = requests.get(
                NAUKRI_API_URL,
                params=params,
                headers=NAUKRI_API_HEADERS,
                timeout=15,
            )

            if resp.status_code != 200:
                logger.debug(f"  Naukri API returned {resp.status_code}, falling back to HTML")
                return []

            data = resp.json()
            jobs = data.get("jobDetails", [])

            for job in jobs:
                title = job.get("title", "")
                company = job.get("companyName", "Unknown")
                location_list = job.get("placeholders", [])
                location = ""
                experience = ""
                salary = "Not disclosed"

                for ph in location_list:
                    if ph.get("type") == "location":
                        location = ph.get("label", "Not specified")
                    elif ph.get("type") == "experience":
                        experience = ph.get("label", "")
                    elif ph.get("type") == "salary":
                        salary = ph.get("label", "Not disclosed")

                job_id = job.get("jdURL", "")
                if job_id:
                    apply_url = f"https://www.naukri.com{job_id}" if not job_id.startswith("http") else job_id
                else:
                    continue

                description = job.get("jobDescription", "")

                if title:
                    listings.append({
                        "title": title,
                        "company": company,
                        "location": location,
                        "experience": experience,
                        "stipend": salary,
                        "apply_url": apply_url,
                        "description": description[:500],
                        "source": "naukri",
                    })

            logger.info(f"  [Naukri API] Got {len(listings)} listing(s)")

        except Exception as e:
            logger.warning(f"  [Naukri API] Search failed: {e}")

        return listings

    def search(self, profile: dict) -> list[dict]:
        """Search for jobs on Naukri using keywords from profile."""
        if self.blocked:
            return []

        # Check if Naukri credentials exist (needed for apply, not search)
        email = os.getenv("NAUKRI_EMAIL", "")
        if not email:
            logger.warning("[Naukri] NAUKRI_EMAIL not set — search only, apply will fail")

        all_listings: list[dict] = []
        seen_urls: set[str] = set()
        keywords = profile.get("keywords", ["software developer internship"])

        logger.info(f"[Naukri] Searching with {len(keywords)} keyword(s)...")

        session = requests.Session()

        # Try API first, fall back to HTML scraping
        for kw in keywords[:5]:
            # API search
            api_results = self._scrape_api(kw)
            for listing in api_results:
                if listing["apply_url"] not in seen_urls:
                    seen_urls.add(listing["apply_url"])
                    all_listings.append(listing)

            # If API returned nothing, try HTML scraping
            if not api_results:
                slug = kw.strip().lower().replace(" ", "-")
                url = f"https://www.naukri.com/{slug}-jobs"
                html_results = self._scrape_html(url, session)
                for listing in html_results:
                    if listing["apply_url"] not in seen_urls:
                        seen_urls.add(listing["apply_url"])
                        all_listings.append(listing)

            # Rate limit between searches
            time.sleep(random.uniform(2.0, 4.0))

        logger.info(f"[Naukri] ✓ Found {len(all_listings)} unique listing(s)")
        return all_listings

    def apply(self, listing: dict, cover_note: str, profile: dict, driver: Any) -> dict:
        """Apply to a Naukri job listing via Selenium."""
        if self.blocked:
            return {"success": False, "message": "Platform blocked by circuit breaker"}

        try:
            if listing.get("source") != "naukri":
                return {"success": False, "message": "Not a Naukri listing"}

            if os.getenv("DRY_RUN", "false").lower() == "true":
                logger.info(f"  [DRY RUN] Would apply to {listing.get('title')} @ {listing.get('company')}")
                return {"success": True, "message": "Dry run — not submitted"}

            apply_url = listing.get("apply_url", "")

            # Import utilities
            from utils.real_mouse import real_click, bring_browser_to_front
            from utils.human_sim import simulate_page_read, random_idle
            from utils.otp_handler import handle_otp_if_present
            from agent.form_filler import fill_form_fields

            # ── Step 1: Navigate to listing ────────────────────────────────
            logger.info(f"[Naukri] Navigating to: {apply_url}")

            # Human-like: briefly visit homepage first
            try:
                driver.get("https://www.naukri.com/")
                random_idle(2.0, 4.0)
                human_scroll(driver, direction="down")
                random_idle(1.0, 2.0)
            except Exception:
                pass

            driver.get(apply_url)
            random_idle(3.0, 6.0)

            # Check if we hit a login wall
            current_url = driver.current_url.lower()
            if "login" in current_url or "nlogin" in current_url:
                logger.warning("[Naukri] Redirected to login page — not authenticated")
                return {"success": False, "message": "Not logged in — login required"}

            # Check for 404
            if "404" in driver.title.lower() or "not found" in driver.page_source.lower():
                return {"success": False, "message": "Listing page not found (404)"}

            # CAPTCHA check
            page_source_lower = driver.page_source.lower()
            if "captcha" in page_source_lower or "unusual activity" in page_source_lower:
                if os.getenv("HEADLESS", "true").lower() == "false":
                    logger.warning("  ⚠️ Captcha detected! Waiting up to 60s for manual solve...")
                    for _ in range(20):
                        time.sleep(3)
                        if "captcha" not in driver.page_source.lower():
                            logger.info("  ✓ Captcha solved!")
                            break
                    else:
                        self.record_captcha()
                        return {"success": False, "message": "Blocked by CAPTCHA (timeout)"}
                else:
                    self.record_captcha()
                    return {"success": False, "message": "Blocked by CAPTCHA"}

            # ── Step 2: Check for "Already Applied" ────────────────────────
            if "already applied" in page_source_lower or "applied" in page_source_lower:
                # Be more specific — look for actual "already applied" indicators
                try:
                    already_el = driver.find_element(
                        "xpath",
                        "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'already applied')]"
                    )
                    if already_el.is_displayed():
                        return {"success": False, "message": "Already applied to this listing"}
                except Exception:
                    pass

            # ── Step 3: Find and click Apply button ────────────────────────
            logger.info("[Naukri] Looking for Apply button...")

            apply_btn = None
            apply_selectors = [
                "button#apply-button",
                "button.apply-button",
                "button[id*='apply']",
                "a.apply-button",
                "button.styles_apply-button",
                "button[class*='apply']",
                "a[class*='apply']",
                "#applyButton",
                ".apply-button-container button",
            ]

            for selector in apply_selectors:
                try:
                    btn = driver.find_element("css selector", selector)
                    if btn.is_displayed() and btn.is_enabled():
                        apply_btn = btn
                        logger.info(f"  Found Apply button via: {selector}")
                        break
                except Exception:
                    continue

            # XPath fallback
            if not apply_btn:
                xpath_options = [
                    "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'apply')]",
                    "//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'apply')]",
                    "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'i am interested')]",
                ]
                for xpath in xpath_options:
                    try:
                        btn = driver.find_element("xpath", xpath)
                        if btn.is_displayed() and btn.is_enabled():
                            apply_btn = btn
                            logger.info(f"  Found Apply button via XPath")
                            break
                    except Exception:
                        continue

            if not apply_btn:
                # Check if it's an "external apply" listing
                try:
                    ext_btn = driver.find_element(
                        "xpath",
                        "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'apply on company')]"
                    )
                    if ext_btn.is_displayed():
                        return {"success": False, "message": "External company website apply (Manual required)"}
                except Exception:
                    pass

                return {"success": False, "message": "Apply button not found"}

            # Click Apply
            try:
                bring_browser_to_front(driver)
                real_click(driver, apply_btn)
            except Exception:
                driver.execute_script("arguments[0].click();", apply_btn)

            logger.info("  ✓ Clicked Apply button (real mouse)")
            random_idle(2.0, 4.0)

            # ── Step 4: Handle OTP if required ─────────────────────────────
            if not handle_otp_if_present(driver, platform="Naukri", timeout=120):
                self.record_captcha()
                return {"success": False, "message": "OTP verification timed out"}

            # ── Step 5: Fill application form ──────────────────────────────
            logger.info("[Naukri] Filling application form...")

            # Naukri may open a modal or a new page with the application form
            # Give it time to load
            random_idle(2.0, 3.0)

            # Fill all visible form fields using smart form filler
            filled = fill_form_fields(driver, profile)
            logger.info(f"  Filled {filled} form field(s)")

            # Look for chatbot/questionnaire panel (Naukri uses this sometimes)
            try:
                chatbot_inputs = driver.find_elements(
                    "css selector",
                    ".chatbot-input, .questionnaire textarea, .apply-form textarea"
                )
                for inp in chatbot_inputs:
                    if inp.is_displayed() and not (inp.get_attribute("value") or "").strip():
                        from agent.form_filler import answer_question, _get_field_label
                        label = _get_field_label(driver, inp)
                        if label:
                            answer = answer_question(label, profile)
                            inp.send_keys(answer)
                            logger.info(f"  ✓ Filled chatbot question: {label[:30]}...")
                            random_idle(0.5, 1.5)
            except Exception:
                pass

            # ── Step 6: Handle resume upload ───────────────────────────────
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

            # ── Step 7: Submit ─────────────────────────────────────────────
            logger.info("[Naukri] Looking for Submit button...")

            submit_btn = None
            submit_selectors = [
                "button[type='submit']",
                "button#submit",
                "button.submit-button",
                "button[class*='submit']",
                "input[type='submit']",
            ]

            for selector in submit_selectors:
                try:
                    btn = driver.find_element("css selector", selector)
                    if btn.is_displayed() and btn.is_enabled():
                        submit_btn = btn
                        break
                except Exception:
                    continue

            # XPath fallback for submit
            if not submit_btn:
                xpath_submit = [
                    "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'submit')]",
                    "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'apply')]",
                    "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'send')]",
                ]
                for xpath in xpath_submit:
                    try:
                        btn = driver.find_element("xpath", xpath)
                        if btn.is_displayed() and btn.is_enabled():
                            submit_btn = btn
                            break
                    except Exception:
                        continue

            if submit_btn:
                try:
                    real_click(driver, submit_btn)
                except Exception:
                    driver.execute_script("arguments[0].click();", submit_btn)
                logger.info("  ✓ Clicked Submit (real mouse)")
                random_idle(3.0, 5.0)
            else:
                # Some Naukri listings are 1-click apply (no separate submit)
                logger.info("  No separate Submit button — may be 1-click apply")

            # ── Step 8: Handle post-submit OTP ─────────────────────────────
            if not handle_otp_if_present(driver, platform="Naukri", timeout=120):
                return {"success": False, "message": "Post-submit OTP timed out"}

            # ── Step 9: Verify success ─────────────────────────────────────
            page = driver.page_source.lower()
            success_indicators = [
                "application submitted",
                "successfully applied",
                "your application has been",
                "applied successfully",
                "thank you for applying",
                "application sent",
                "resume sent",
                "congratulations",
            ]

            if any(s in page for s in success_indicators):
                self.captcha_count = 0
                logger.info(f"[Naukri] ✅ Successfully applied to {listing.get('title')} @ {listing.get('company')}")
                return {"success": True, "message": "Naukri application submitted successfully"}

            # If no clear success, but we clicked apply and submit without errors
            self.captcha_count = 0
            return {
                "success": True,
                "message": "Naukri application likely submitted (1-click or form completed)",
            }

        except Exception as e:
            logger.error(f"[Naukri] ✗ Error during application: {e}")
            return {"success": False, "message": f"Error: {str(e)}"}
