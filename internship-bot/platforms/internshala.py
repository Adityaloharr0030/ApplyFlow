"""
platforms/internshala.py
────────────────────────
Adapter for Internshala.
Combines search functionality (requests/bs4) and application functionality (Selenium).
"""

import logging
import random
import time
import os
import requests
from bs4 import BeautifulSoup
from typing import Any
from .base import Platform
from agent.form_filler import answer_question

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://internshala.com/",
}

BASE_URLS = [
    "https://internshala.com/internships/computer-science-internship",
]

class InternshalaPlatform(Platform):
    def __init__(self):
        super().__init__()

    def _build_keyword_urls(self, profile: dict) -> list[str]:
        urls = []
        keywords = profile.get("keywords", [])
        for kw in keywords:
            slug = kw.strip().lower().replace(" ", "-")
            url = f"https://internshala.com/internships/{slug}-internship"
            if url not in BASE_URLS:
                urls.append(url)
        return urls

    def _parse_listing_card(self, card) -> dict | None:
        try:
            title_tag = card.select_one("h2.job-internship-name, a.job-title-href, h3.job-internship-name")
            title = title_tag.get_text(strip=True) if title_tag else None

            company_tag = card.select_one("p.company-name, .company_name a, h4.company_name")
            company = company_tag.get_text(strip=True) if company_tag else "Unknown"

            location_tag = card.select_one(".row-1-item.locations span, #location_names a, .location_link")
            location = location_tag.get_text(strip=True) if location_tag else "Not specified"

            row_items = card.select(".row-1-item")
            if len(row_items) >= 3:
                duration_span = row_items[2].select_one("span")
                duration = duration_span.get_text(strip=True) if duration_span else "N/A"
            else:
                duration = "N/A"

            stipend_tag = card.select_one(".stipend, span.desktop-text")
            stipend = stipend_tag.get_text(strip=True) if stipend_tag else "Unpaid / Not listed"

            link_tag = card.select_one("a.job-title-href, a[href*='/internship/detail/']")
            if link_tag and link_tag.get("href"):
                href = link_tag["href"]
                apply_url = href if href.startswith("http") else f"https://internshala.com{href}"
            else:
                card_link = card.find("a", href=True)
                if card_link:
                    href = card_link["href"]
                    apply_url = href if href.startswith("http") else f"https://internshala.com{href}"
                else:
                    apply_url = None

            if not title or not apply_url:
                return None

            return {
                "title": title,
                "company": company,
                "location": location,
                "duration": duration,
                "stipend": stipend,
                "apply_url": apply_url,
                "source": "internshala",
            }
        except Exception as e:
            logger.debug(f"Failed to parse listing card: {e}")
            return None

    def _scrape_page_internal(self, url: str, session: requests.Session) -> list[dict]:
        listings = []
        try:
            logger.info(f"  ↳ Fetching: {url}")
            resp = session.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")

            cards = soup.select(
                ".individual_internship, "
                ".internship_meta, "
                ".individual_internship_header, "
                "div[class*='internship_']"
            )

            if not cards:
                cards = soup.select("#internship_list_container_1 .container-fluid")

            if not cards:
                logger.debug("Using fallback link-based extraction")
                links = soup.select("a[href*='/internship/detail/']")
                seen_urls = set()
                for link in links:
                    href = link.get("href", "")
                    full_url = href if href.startswith("http") else f"https://internshala.com{href}"
                    if full_url not in seen_urls:
                        seen_urls.add(full_url)
                        title = link.get_text(strip=True) or "Internship"
                        listings.append({
                            "title": title,
                            "company": "Unknown",
                            "location": "Not specified",
                            "duration": "N/A",
                            "stipend": "Not listed",
                            "apply_url": full_url,
                            "source": "internshala",
                        })
                return listings

            for card in cards:
                parsed = self._parse_listing_card(card)
                if parsed:
                    listings.append(parsed)

        except requests.exceptions.RequestException as e:
            logger.warning(f"  ✗ Network error scraping {url}: {e}")
        except Exception as e:
            logger.warning(f"  ✗ Unexpected error scraping {url}: {e}")

        return listings

    def _scrape_page_with_retry(self, url: str, session: requests.Session, max_retries: int = 3) -> list[dict]:
        for attempt in range(1, max_retries + 1):
            result = self._scrape_page_internal(url, session)
            if result:
                return result
            if attempt < max_retries:
                wait = 2 ** attempt
                logger.info(f"  Retry {attempt}/{max_retries} in {wait}s for {url}")
                time.sleep(wait)
        return []

    def search(self, profile: dict) -> list[dict]:
        if self.blocked:
            return []
        all_listings: list[dict] = []
        seen_urls: set[str] = set()

        urls = list(BASE_URLS) + self._build_keyword_urls(profile)
        logger.info(f"[Internshala] Scraping {len(urls)} search URL(s)…")

        session = requests.Session()

        for base_url in urls:
            for page in range(1, 3):
                if page > 1:
                    separator = "&" if "?" in base_url else "?"
                    page_url = f"{base_url}{separator}page={page}"
                else:
                    page_url = base_url
                page_listings = self._scrape_page_with_retry(page_url, session)

                for listing in page_listings:
                    if listing["apply_url"] not in seen_urls:
                        seen_urls.add(listing["apply_url"])
                        all_listings.append(listing)

                delay = random.uniform(2.0, 3.0)
                logger.debug(f"  ⏳ Sleeping {delay:.1f}s before next request…")
                time.sleep(delay)

        logger.info(f"[Internshala] ✓ Found {len(all_listings)} unique listing(s)")
        return all_listings

    def apply(self, listing: dict, cover_note: str, profile: dict, driver: Any) -> dict:
        if self.blocked:
            return {"success": False, "message": "Platform blocked by circuit breaker"}

        try:
            if listing.get("source") != "internshala":
                return {"success": False, "message": "Not an Internshala listing"}

            if os.getenv("DRY_RUN", "false").lower() == "true":
                logger.info(f"  [DRY RUN] Would apply to {listing.get('title')} @ {listing.get('company')}")
                return {"success": True, "message": "Dry run — not submitted"}

            from utils.real_mouse import real_click, real_scroll, bring_browser_to_front
            from utils.human_sim import random_idle
            from utils.otp_handler import handle_otp_if_present
            from agent.form_filler import fill_form_fields, answer_question
            try:
                from agent.action_trainer import record_action
            except ImportError:
                def record_action(*a, **kw): pass

            apply_url = listing.get("apply_url", "")
            record_action("browser_open", platform="internshala",
                          listing_title=listing.get("title", ""),
                          company=listing.get("company", ""), url=apply_url)

            # Human-like warm-up: briefly visit homepage before jumping to listing
            try:
                driver.get("https://internshala.com/internships")
                random_idle(2.5, 5.0)
                bring_browser_to_front(driver)
                real_scroll(driver, direction="down")
                random_idle(0.8, 2.0)
            except Exception:
                pass

            logger.info(f"[Internshala] Navigating to: {apply_url}")
            driver.get(apply_url)
            random_idle(3.5, 6.5)

            if "404" in driver.title.lower() or "not found" in driver.page_source.lower():
                return {"success": False, "message": "Listing page not found (404)"}

            if "captcha" in driver.page_source.lower() or "unusual activity" in driver.page_source.lower():
                if os.getenv("HEADLESS", "true").lower() == "false":
                    logger.warning("  ⚠️ Captcha detected! You have 60 seconds to solve it manually...")
                    for _ in range(20):
                        time.sleep(3)
                        if "captcha" not in driver.page_source.lower() and "unusual activity" not in driver.page_source.lower():
                            logger.info("  ✓ Captcha solved! Continuing...")
                            break
                    else:
                        self.record_captcha()
                        return {"success": False, "message": "Blocked by CAPTCHA (Timed out)"}
                else:
                    self.record_captcha()
                    return {"success": False, "message": "Blocked by CAPTCHA"}

            # Check if we're logged in
            page_source_raw = driver.page_source
            if "is_guest = 1" in page_source_raw or "is_guest=1" in page_source_raw:
                logger.warning("[Internshala] Not logged in (guest user)")
                return {"success": False, "message": "Not logged in — login required"}

            if "login" in driver.current_url.lower() or "registration" in driver.current_url.lower():
                logger.warning("[Internshala] Redirected to login page")
                return {"success": False, "message": "Redirected to login — not authenticated"}

            # ── Find and click Apply button ────────────────────────────────
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
                        real_click(driver, btn)
                        apply_clicked = True
                        logger.info("  ✓ Clicked Apply Now button (real mouse)")
                        record_action("click_apply", platform="internshala", element="Apply Now button",
                                      listing_title=listing.get("title", ""), company=listing.get("company", ""),
                                      url=apply_url)
                        random_idle(2.0, 3.0)
                        break
                except Exception:
                    continue

            if not apply_clicked:
                try:
                    from selenium.webdriver.common.by import By
                    btn = driver.find_element(By.PARTIAL_LINK_TEXT, "Apply")
                    real_click(driver, btn)
                    apply_clicked = True
                    random_idle(2.0, 3.0)
                except Exception:
                    pass

            if not apply_clicked:
                logger.warning("[Internshala] Could not find Apply button")
                return {"success": False, "message": "Could not find Apply Now button"}

            # ── Fill cover letter ──────────────────────────────────────────
            cover_selectors = [
                "textarea#cover_letter",
                "textarea[name='cover_letter']",
                "textarea.cover_letter",
                "textarea#text_input",
                "textarea[placeholder*='cover']",
                "textarea[placeholder*='Cover']",
                ".ql-editor",
            ]

            for selector in cover_selectors:
                try:
                    textarea = driver.find_element("css selector", selector)
                    if textarea.is_displayed():
                        textarea.clear()
                        textarea.send_keys(cover_note)
                        logger.info("  ✓ Filled cover letter textarea")
                        random_idle(1.0, 2.0)
                        break
                except Exception:
                    continue

            # ── Smart form filling (dropdowns, radios, extra fields) ───────
            filled = fill_form_fields(
                driver, profile,
                skip_selectors=["textarea#cover_letter", "textarea[name='cover_letter']"]
            )
            if filled > 0:
                logger.info(f"  ✓ Smart-filled {filled} additional form field(s)")

            # ── Handle resume upload ───────────────────────────────────────
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

            # ── Handle OTP if required ─────────────────────────────────────
            if not handle_otp_if_present(driver, platform="Internshala", timeout=120):
                self.record_captcha()
                return {"success": False, "message": "OTP verification timed out"}

            # ── Submit ─────────────────────────────────────────────────────
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
                        real_click(driver, btn)
                        submit_clicked = True
                        logger.info("  ✓ Clicked Submit button (real mouse)")
                        random_idle(3.0, 5.0)
                        break
                except Exception:
                    continue

            if not submit_clicked:
                logger.warning("[Internshala] Could not find Submit button")
                return {"success": False, "message": "Could not find Submit button"}

            # ── Post-submit OTP check ──────────────────────────────────────
            if not handle_otp_if_present(driver, platform="Internshala", timeout=120):
                return {"success": False, "message": "Post-submit OTP timed out"}

            # ── Verify success ─────────────────────────────────────────────
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
                record_action("apply_success", platform="internshala",
                              listing_title=listing.get("title", ""), company=listing.get("company", ""),
                              url=apply_url)
                self.captcha_count = 0
                return {"success": True, "message": "Application submitted successfully"}

            return {
                "success": True,
                "message": "Submit clicked but confirmation uncertain — check manually",
            }

        except Exception as e:
            logger.error(f"[Internshala] ✗ Error during application: {e}")
            return {"success": False, "message": f"Error: {str(e)}"}


