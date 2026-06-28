"""
scraper/internshala.py
──────────────────────
Scrapes internship listings from Internshala using requests + BeautifulSoup.
- Searches the computer-science category + keyword-specific pages
- Handles pagination (first 2 pages)
- 2–3 second random delay between requests to avoid rate-limiting
- Returns empty list on any error — never crashes the bot
"""

import logging
import random
import time
from typing import Any

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Standard headers to mimic a real browser visit
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

# Base search URLs — we combine the main CS page + keyword-specific pages
BASE_URLS = [
    "https://internshala.com/internships/computer-science-internship",
]


def _build_keyword_urls(profile: dict) -> list[str]:
    """
    Generate Internshala search URLs from the candidate's keywords.
    Internshala URL pattern: /internships/{keyword}-internship
    """
    urls = []
    keywords = profile.get("keywords", [])
    for kw in keywords:
        # Convert "Full Stack" → "full+stack", spaces become hyphens in Internshala URLs
        slug = kw.strip().lower().replace(" ", "-")
        url = f"https://internshala.com/internships/{slug}-internship"
        if url not in BASE_URLS:
            urls.append(url)
    return urls


def _parse_listing_card(card) -> dict[str, Any] | None:
    """
    Parse a single internship listing card from the Internshala HTML.
    Returns a dict with title, company, location, duration, stipend, apply_url, source.
    Returns None if essential fields are missing.
    """
    try:
        # --- Title ---
        title_tag = card.select_one("h2.job-internship-name, a.job-title-href, h3.job-internship-name")
        title = title_tag.get_text(strip=True) if title_tag else None

        # --- Company ---
        company_tag = card.select_one("p.company-name, .company_name a, h4.company_name")
        company = company_tag.get_text(strip=True) if company_tag else "Unknown"

        # --- Location ---
        location_tag = card.select_one(
            ".row-1-item.locations span, #location_names a, .location_link"
        )
        location = location_tag.get_text(strip=True) if location_tag else "Not specified"

        # --- Duration ---
        # Duration is typically the 3rd .row-1-item span (after location and stipend)
        row_items = card.select(".row-1-item")
        if len(row_items) >= 3:
            duration_span = row_items[2].select_one("span")
            duration = duration_span.get_text(strip=True) if duration_span else "N/A"
        else:
            duration = "N/A"

        # --- Stipend ---
        stipend_tag = card.select_one(".stipend, span.desktop-text")
        stipend = stipend_tag.get_text(strip=True) if stipend_tag else "Unpaid / Not listed"

        # --- Apply URL ---
        link_tag = card.select_one("a.job-title-href, a[href*='/internship/detail/']")
        if link_tag and link_tag.get("href"):
            href = link_tag["href"]
            apply_url = href if href.startswith("http") else f"https://internshala.com{href}"
        else:
            # Try the card-level link
            card_link = card.find("a", href=True)
            if card_link:
                href = card_link["href"]
                apply_url = href if href.startswith("http") else f"https://internshala.com{href}"
            else:
                apply_url = None

        # Skip if we couldn't extract a title or URL
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


def _scrape_page(url: str, session: requests.Session) -> list[dict]:
    """
    Fetch a single Internshala page and extract all internship listings from it.
    """
    listings = []
    try:
        logger.info(f"  ↳ Fetching: {url}")
        resp = session.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        # Internshala wraps each listing in a container div
        cards = soup.select(
            ".individual_internship, "
            ".internship_meta, "
            ".individual_internship_header, "
            "div[class*='internship_']"
        )

        # Fallback: if no specific cards found, try broader approach
        if not cards:
            cards = soup.select("#internship_list_container_1 .container-fluid")

        # Broader fallback — look for any link that points to internship detail pages
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
            parsed = _parse_listing_card(card)
            if parsed:
                listings.append(parsed)

    except requests.exceptions.RequestException as e:
        logger.warning(f"  ✗ Network error scraping {url}: {e}")
    except Exception as e:
        logger.warning(f"  ✗ Unexpected error scraping {url}: {e}")

    return listings


def scrape_internshala(profile: dict) -> list[dict]:
    """
    Main entry point — scrapes Internshala for internship listings.

    Args:
        profile: Candidate profile dict (used to build keyword search URLs).

    Returns:
        List of listing dicts. Empty list on total failure.
    """
    all_listings: list[dict] = []
    seen_urls: set[str] = set()

    # Build the full set of URLs to scrape
    urls = list(BASE_URLS) + _build_keyword_urls(profile)
    logger.info(f"[Internshala] Scraping {len(urls)} search URL(s)…")

    session = requests.Session()

    for base_url in urls:
        # Scrape first 2 pages for each search URL
        for page in range(1, 3):
            page_url = f"{base_url}/page-{page}" if page > 1 else base_url
            page_listings = _scrape_page(page_url, session)

            for listing in page_listings:
                # Deduplicate by URL within this scraper run
                if listing["apply_url"] not in seen_urls:
                    seen_urls.add(listing["apply_url"])
                    all_listings.append(listing)

            # Polite delay: 2–3 seconds between requests
            delay = random.uniform(2.0, 3.0)
            logger.debug(f"  ⏳ Sleeping {delay:.1f}s before next request…")
            time.sleep(delay)

    logger.info(f"[Internshala] ✓ Found {len(all_listings)} unique listing(s)")
    return all_listings
