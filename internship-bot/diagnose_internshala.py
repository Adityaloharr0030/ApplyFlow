"""Detailed Internshala diagnostic to check all field selectors."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://internshala.com/",
}

r = requests.get("https://internshala.com/internships/computer-science-internship", headers=HEADERS, timeout=15)
soup = BeautifulSoup(r.text, "html.parser")

cards = soup.select(".individual_internship")
print(f"Found {len(cards)} cards")

if cards:
    card = cards[0]
    print("\n=== FULL CARD HTML ===")
    print(card.prettify()[:4000])
    
    print("\n=== FIELD EXTRACTION TEST ===")
    
    # Title
    for sel in ["h3.job-internship-name", "h2.job-internship-name", "a.job-title-href", ".profile h3", ".profile h2"]:
        el = card.select_one(sel)
        print(f"  Title '{sel}': {el.get_text(strip=True) if el else 'NOT FOUND'}")
    
    # Company
    for sel in ["p.company-name", ".company_name a", "h4.company_name", ".company-name", "a.link_display_like_text"]:
        el = card.select_one(sel)
        print(f"  Company '{sel}': {el.get_text(strip=True) if el else 'NOT FOUND'}")
    
    # Location
    for sel in [".row-1-item.locations span", "#location_names a", ".location_link", ".locations span", "a#location_names"]:
        el = card.select_one(sel)
        print(f"  Location '{sel}': {el.get_text(strip=True) if el else 'NOT FOUND'}")
    
    # Stipend
    for sel in [".stipend", "span.desktop-text", ".stipend_container_desktop span"]:
        el = card.select_one(sel)
        print(f"  Stipend '{sel}': {el.get_text(strip=True) if el else 'NOT FOUND'}")
    
    # Duration
    items = card.select(".row-1-item .item_body")
    print(f"  Duration '.row-1-item .item_body': {items[0].get_text(strip=True) if items else 'NOT FOUND'}")
    
    # Link
    for sel in ["a.job-title-href", "a[href*='/internship/detail/']"]:
        el = card.select_one(sel)
        print(f"  Link '{sel}': {el.get('href') if el else 'NOT FOUND'}")
