"""
scraper/linkedin.py
───────────────────
Scrapes internship listings from LinkedIn using Selenium + undetected-chromedriver.
- Logs in with credentials from .env
- Searches for internships matching the candidate's skills
- Scrapes top 10 results
- Handles login walls and bot detection gracefully
- Returns empty list on any error — never crashes the bot
"""

import logging
import os
import random
import time
from typing import Any

logger = logging.getLogger(__name__)


def _create_driver():
    """
    Create an undetected Chrome WebDriver instance.
    Returns None if Chrome or chromedriver aren't available.
    """
    try:
        import undetected_chromedriver as uc

        options = uc.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--window-size=1920,1080")
        # Run headless for automation (comment out for debugging)
        options.add_argument("--headless=new")

        driver = uc.Chrome(options=options, use_subprocess=True)
        driver.implicitly_wait(10)
        return driver
    except Exception as e:
        logger.error(f"[LinkedIn] Failed to create Chrome driver: {e}")
        return None


def _login(driver, email: str, password: str) -> bool:
    """
    Log into LinkedIn with the provided credentials.
    Returns True on success, False on failure.
    """
    try:
        logger.info("[LinkedIn] Navigating to login page…")
        driver.get("https://www.linkedin.com/login")
        time.sleep(random.uniform(2.0, 4.0))

        # Fill email
        email_field = driver.find_element("id", "username")
        email_field.clear()
        email_field.send_keys(email)
        time.sleep(random.uniform(0.5, 1.0))

        # Fill password
        password_field = driver.find_element("id", "password")
        password_field.clear()
        password_field.send_keys(password)
        time.sleep(random.uniform(0.5, 1.0))

        # Click sign in
        sign_in_btn = driver.find_element(
            "css selector", "button[type='submit'], .login__form_action_container button"
        )
        sign_in_btn.click()
        time.sleep(random.uniform(3.0, 5.0))

        # Check if we landed on the feed (successful login)
        current_url = driver.current_url
        if "feed" in current_url or "mynetwork" in current_url or "jobs" in current_url:
            logger.info("[LinkedIn] ✓ Login successful")
            return True

        # Check for CAPTCHA or verification challenge
        page_source = driver.page_source.lower()
        if "checkpoint" in current_url or "challenge" in current_url:
            logger.warning("[LinkedIn] ✗ Hit security checkpoint/CAPTCHA — skipping")
            return False

        if "verify" in page_source or "captcha" in page_source:
            logger.warning("[LinkedIn] ✗ Verification required — skipping")
            return False

        # Might still be logged in — check for feed elements
        logger.info("[LinkedIn] Login status unclear, attempting to continue…")
        return True

    except Exception as e:
        logger.error(f"[LinkedIn] Login failed: {e}")
        return False


def _parse_job_card(card) -> dict[str, Any] | None:
    """
    Parse a single LinkedIn job card element into a listing dict.
    """
    try:
        # Title
        title_el = card.find_element(
            "css selector",
            "a.job-card-list__title, "
            ".job-card-container__link, "
            "a[class*='job-card'] strong, "
            ".artdeco-entity-lockup__title a"
        )
        title = title_el.text.strip() if title_el else None

        # Company
        try:
            company_el = card.find_element(
                "css selector",
                ".job-card-container__primary-description, "
                ".artdeco-entity-lockup__subtitle span, "
                ".job-card-container__company-name"
            )
            company = company_el.text.strip()
        except Exception:
            company = "Unknown"

        # Location
        try:
            location_el = card.find_element(
                "css selector",
                ".job-card-container__metadata-wrapper li, "
                ".artdeco-entity-lockup__caption span, "
                ".job-card-container__metadata-item"
            )
            location = location_el.text.strip()
        except Exception:
            location = "Not specified"

        # Apply URL
        try:
            link_el = card.find_element(
                "css selector",
                "a.job-card-list__title, "
                "a.job-card-container__link, "
                "a[class*='job-card']"
            )
            apply_url = link_el.get_attribute("href") or ""
            # Clean tracking params
            if "?" in apply_url:
                apply_url = apply_url.split("?")[0]
        except Exception:
            apply_url = None

        if not title or not apply_url:
            return None

        return {
            "title": title,
            "company": company,
            "location": location,
            "apply_url": apply_url,
            "source": "linkedin",
        }
    except Exception as e:
        logger.debug(f"Failed to parse LinkedIn card: {e}")
        return None


def scrape_linkedin(profile: dict) -> list[dict]:
    """
    Main entry point — scrapes LinkedIn for internship listings.

    Args:
        profile: Candidate profile dict.

    Returns:
        List of listing dicts. Empty list on total failure.
    """
    # Get LinkedIn credentials from environment
    email = os.getenv("LINKEDIN_EMAIL", "")
    password = os.getenv("LINKEDIN_PASSWORD", "")

    if not email or not password:
        logger.warning("[LinkedIn] ✗ No credentials in .env — skipping LinkedIn scraper")
        return []

    driver = None
    all_listings: list[dict] = []

    try:
        # Create browser
        driver = _create_driver()
        if not driver:
            return []

        # Login
        if not _login(driver, email, password):
            logger.warning("[LinkedIn] ✗ Login failed — returning empty results")
            return []

        # Build search query from profile skills/keywords
        search_terms = ["internship"]
        keywords = profile.get("keywords", [])[:3]  # Top 3 keywords
        search_terms.extend(keywords)
        query = " ".join(search_terms)

        # Navigate to LinkedIn Jobs search
        search_url = (
            f"https://www.linkedin.com/jobs/search/"
            f"?keywords={query.replace(' ', '%20')}"
            f"&location=India"
            f"&f_WT=2"  # Remote filter
            f"&sortBy=DD"  # Sort by date
        )

        logger.info(f"[LinkedIn] Searching: {query}")
        driver.get(search_url)
        time.sleep(random.uniform(3.0, 5.0))

        # Check for bot detection
        page_source = driver.page_source.lower()
        if "captcha" in page_source or "unusual activity" in page_source:
            logger.warning("[LinkedIn] ✗ Bot detection triggered — skipping")
            return []

        # Scroll to load more results
        for _ in range(3):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(random.uniform(1.0, 2.0))

        # Extract job cards
        try:
            cards = driver.find_elements(
                "css selector",
                ".job-card-container, "
                ".jobs-search-results__list-item, "
                ".scaffold-layout__list-item, "
                "li[class*='jobs-search']"
            )
        except Exception:
            cards = []

        logger.info(f"[LinkedIn] Found {len(cards)} job card(s) on page")

        # Parse up to 10 cards
        seen_urls: set[str] = set()
        for card in cards[:15]:  # Check up to 15, keep max 10
            parsed = _parse_job_card(card)
            if parsed and parsed["apply_url"] not in seen_urls:
                seen_urls.add(parsed["apply_url"])
                all_listings.append(parsed)
                if len(all_listings) >= 10:
                    break

        logger.info(f"[LinkedIn] ✓ Extracted {len(all_listings)} unique listing(s)")

    except Exception as e:
        logger.error(f"[LinkedIn] ✗ Unexpected error: {e}")
    finally:
        # Always close the browser
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

    return all_listings
