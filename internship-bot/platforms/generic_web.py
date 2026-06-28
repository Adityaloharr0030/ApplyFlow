"""
platforms/generic_web.py
────────────────────────
Adapter for Generic Web / Target Companies / Cold Outreach.
"""

import logging
import random
import time
import os
import requests
from bs4 import BeautifulSoup
from typing import Any
from .base import Platform
import re

# Use the existing cold email logic
from utils.email_send import send_cold_email

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    )
}

class GenericWebPlatform(Platform):
    def __init__(self):
        super().__init__()
        self.emailed_domains = set()

    def search(self, profile: dict) -> list[dict]:
        """
        Creates synthetic listings from 'target_companies' in the profile.
        These listings will trigger the cold email/ATS fallback during the apply step.
        """
        target_companies = profile.get("target_companies", [])
        listings = []
        for company in target_companies:
            listings.append({
                "title": "Software Engineering Internship", # Default guess
                "company": company,
                "location": "Remote / HQ",
                "apply_url": f"https://{company}/careers" if not company.startswith("http") else company,
                "source": "generic_web",
            })
            
        if listings:
            logger.info(f"[GenericWeb] Generated {len(listings)} synthetic listing(s) from target_companies.")
        return listings

    def apply(self, listing: dict, cover_note: str, profile: dict, driver: Any) -> dict:
        company = listing.get("company", "Unknown")
        domain = company.replace("https://", "").replace("http://", "").split("/")[0]

        if domain in self.emailed_domains:
            return {"success": False, "message": "Already emailed/applied to this domain in this run."}

        logger.info(f"[GenericWeb] Processing target company: {company}")

        # Check if dry run
        is_dry_run = os.getenv("DRY_RUN", "false").lower() == "true"

        # 1. Open the careers page via Requests to search for an email or ATS links
        apply_url = listing.get("apply_url", f"https://{company}/careers")
        
        try:
            resp = requests.get(apply_url, headers=HEADERS, timeout=10)
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # ATS Detection
            ats_links = []
            for link in soup.find_all("a", href=True):
                href = link["href"]
                if "boards.greenhouse.io" in href or "jobs.lever.co" in href or "ashbyhq.com" in href:
                    ats_links.append(href)
            
            if ats_links:
                ats_url = ats_links[0]
                logger.info(f"  ✓ Found ATS link: {ats_url}")
                if is_dry_run:
                    logger.info("  [DRY RUN] Would attempt to automate ATS form.")
                    self.emailed_domains.add(domain)
                    return {"success": True, "message": "Dry run ATS apply."}
                else:
                    return {"success": False, "message": f"ATS found: {ats_url}. (Manual ATS automation not fully implemented yet)"}

            # Cold Email Fallback
            text = soup.get_text()
            emails = re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', text)
            
            careers_emails = [e for e in emails if "career" in e.lower() or "job" in e.lower() or "hr@" in e.lower()]
            target_email = careers_emails[0] if careers_emails else None
            
            if not target_email and emails:
                target_email = emails[0]
                
            if target_email:
                logger.info(f"  ✓ Found contact email: {target_email}")
                
                if is_dry_run:
                    logger.info(f"  [DRY RUN] Would send cold email to {target_email}")
                    self.emailed_domains.add(domain)
                    return {"success": True, "message": f"Dry run cold email to {target_email}"}
                else:
                    result = send_cold_email(
                        company=company,
                        role=listing.get("title", "Internship"),
                        to_email=target_email,
                        cover_note=cover_note,
                        profile=profile,
                    )
                    if result.get("success"):
                        self.emailed_domains.add(domain)
                    return result

            return {"success": False, "message": "No ATS or Email found."}
            
        except Exception as e:
            logger.warning(f"  ✗ Failed to process company site: {e}")
            return {"success": False, "message": f"Site processing failed: {e}"}
