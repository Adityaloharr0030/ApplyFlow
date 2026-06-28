"""
scraper/linkedin.py
───────────────────
Scrapes internship listings from LinkedIn using the public guest jobs API.
- No login required — uses LinkedIn's guest API endpoint
- No Selenium, no bot detection issues
- Searches for internships matching the candidate's keywords
- Returns top 10 results
- Returns empty list on any error — never crashes the bot
"""

import logging
from typing import Any

import requests
from bs4 import BeautifulSoup

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


def scrape_linkedin(profile: dict) -> list[dict]:
    """
    Main entry point — scrapes LinkedIn for internship listings using the
    public guest jobs API (no login required).

    Args:
        profile: Candidate profile dict.

    Returns:
        List of listing dicts. Empty list on total failure.
    """
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

            if len(listings) >= 10:
                break

        logger.info(f"[LinkedIn] ✓ Found {len(listings)} listing(s)")
        return listings

    except Exception as e:
        logger.warning(f"[LinkedIn] ✗ Failed: {e}")
        return []
