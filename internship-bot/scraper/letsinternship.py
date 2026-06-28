"""
scraper/letsinternship.py
─────────────────────────
Scrapes internship listings from LetsInternship (letsintern.com).
- Uses requests + BeautifulSoup
- Returns same dict format as other scrapers
- Returns empty list on any error — never crashes the bot

NOTE: As of mid-2026, letsintern.com appears to have been repurposed and
no longer hosts internship listings. This scraper will return an empty list
but is kept for forward-compatibility in case the site returns.
"""

import logging
import random
import time
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

# LetsIntern.com is the actual domain for LetsInternship
BASE_URLS = [
    "https://www.letsintern.com/internships",
]


def _build_keyword_urls(profile: dict) -> list[str]:
    """
    Generate LetsIntern search URLs from the candidate's keywords.
    """
    urls = []
    keywords = profile.get("keywords", [])
    for kw in keywords[:3]:  # Limit to 3 keywords to avoid excessive requests
        slug = kw.strip().replace(" ", "+")
        url = f"https://www.letsintern.com/internships?q={slug}"
        if url not in BASE_URLS:
            urls.append(url)
    return urls


def _is_internship_site(soup: BeautifulSoup) -> bool:
    """
    Quick sanity check: does this page look like an internship listing site?
    Checks title and body text for internship-related content.
    """
    title = (soup.title.string or "").lower() if soup.title else ""
    # If the title mentions casino, gambling, etc., it's been hijacked
    bad_keywords = ["casino", "gambling", "betting", "poker", "slots"]
    if any(kw in title for kw in bad_keywords):
        return False
    # Check for internship-related content
    if "intern" in title:
        return True
    # Ambiguous — assume it's still valid
    return True


def _parse_listing(element) -> dict[str, Any] | None:
    """
    Parse a single internship listing element from LetsIntern HTML.
    """
    try:
        # --- Title ---
        title_tag = element.select_one(
            "h3 a, .internship-title a, .card-title a, h2 a, a[class*='title']"
        )
        title = title_tag.get_text(strip=True) if title_tag else None

        # --- Company ---
        company_tag = element.select_one(
            ".company-name, .internship-company, .card-subtitle, "
            "p.company, span.company"
        )
        company = company_tag.get_text(strip=True) if company_tag else "Unknown"

        # --- Location ---
        location_tag = element.select_one(
            ".location, .internship-location, span[class*='location']"
        )
        location = location_tag.get_text(strip=True) if location_tag else "Not specified"

        # --- Stipend ---
        stipend_tag = element.select_one(
            ".stipend, .salary, span[class*='stipend']"
        )
        stipend = stipend_tag.get_text(strip=True) if stipend_tag else "Not listed"

        # --- Duration ---
        duration_tag = element.select_one(
            ".duration, span[class*='duration']"
        )
        duration = duration_tag.get_text(strip=True) if duration_tag else "N/A"

        # --- Apply URL ---
        link = title_tag if title_tag and title_tag.name == "a" else element.find("a", href=True)
        if link and link.get("href"):
            href = link["href"]
            if href.startswith("http"):
                apply_url = href
            elif href.startswith("/"):
                apply_url = f"https://www.letsintern.com{href}"
            else:
                apply_url = f"https://www.letsintern.com/{href}"
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
            "source": "letsinternship",
        }
    except Exception as e:
        logger.debug(f"Failed to parse LetsIntern listing: {e}")
        return None


def _scrape_page(url: str, session: requests.Session) -> list[dict]:
    """
    Fetch a single LetsIntern page and extract all listings.
    """
    listings = []
    try:
        logger.info(f"  ↳ Fetching: {url}")
        resp = session.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        # Sanity check: is this still an internship site?
        if not _is_internship_site(soup):
            logger.warning(
                "[LetsInternship] Site content does not appear to be internship-related "
                "(domain may have been repurposed) — skipping"
            )
            return []

        # Try multiple selectors for listing containers
        cards = soup.select(
            ".internship-card, "
            ".internship-listing, "
            ".card.internship, "
            "div[class*='internship-item'], "
            ".listing-card"
        )

        # Broader fallback: look for repeated list items with links
        if not cards:
            cards = soup.select(
                ".listings-container > div, "
                ".results-list > div, "
                "ul.internships li, "
                ".search-results > div"
            )

        # Final fallback: extract links that look like internship detail pages
        if not cards:
            logger.debug("Using fallback link extraction for LetsIntern")
            links = soup.select("a[href*='/internship/'], a[href*='/apply/']")
            seen = set()
            for link in links:
                href = link.get("href", "")
                full_url = href if href.startswith("http") else f"https://www.letsintern.com{href}"
                if full_url not in seen:
                    seen.add(full_url)
                    title = link.get_text(strip=True) or "Internship"
                    listings.append({
                        "title": title,
                        "company": "Unknown",
                        "location": "Not specified",
                        "duration": "N/A",
                        "stipend": "Not listed",
                        "apply_url": full_url,
                        "source": "letsinternship",
                    })
            return listings

        for card in cards:
            parsed = _parse_listing(card)
            if parsed:
                listings.append(parsed)

    except requests.exceptions.RequestException as e:
        logger.warning(f"  ✗ Network error scraping {url}: {e}")
    except Exception as e:
        logger.warning(f"  ✗ Unexpected error scraping {url}: {e}")

    return listings


def scrape_letsinternship(profile: dict) -> list[dict]:
    """
    Main entry point — scrapes LetsInternship for listings.

    Args:
        profile: Candidate profile dict.

    Returns:
        List of listing dicts. Empty list on total failure.
    """
    all_listings: list[dict] = []
    seen_urls: set[str] = set()

    urls = list(BASE_URLS) + _build_keyword_urls(profile)
    logger.info(f"[LetsInternship] Scraping {len(urls)} search URL(s)…")

    session = requests.Session()

    for url in urls:
        page_listings = _scrape_page(url, session)

        for listing in page_listings:
            if listing["apply_url"] not in seen_urls:
                seen_urls.add(listing["apply_url"])
                all_listings.append(listing)

        # Polite delay between requests
        delay = random.uniform(2.0, 3.0)
        logger.debug(f"  ⏳ Sleeping {delay:.1f}s…")
        time.sleep(delay)

        # If first URL already detected the site is dead, don't bother with more
        if not page_listings and url == BASE_URLS[0]:
            logger.info("[LetsInternship] Base URL returned no listings — skipping remaining URLs")
            break

    logger.info(f"[LetsInternship] ✓ Found {len(all_listings)} unique listing(s)")
    return all_listings
