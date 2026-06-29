"""
tracker/sheets.py
-----------------
Google Sheets logging for internship applications.
- Connects using a service account (credentials from .env)
- Logs each application as a row with full details
- Dedup check: already_applied() prevents re-applying to the same URL
- Graceful fallback: if Google Sheets is unavailable, logs to a local CSV
"""

import csv
import logging
import os
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Local CSV fallback path
CSV_FALLBACK_PATH = Path("./logs/applications.csv")
CSV_HEADERS = [
    "Date",
    "Company",
    "Role",
    "Location",
    "Source",
    "Status",
    "Score",
    "Apply URL",
    "Cover Note Preview",
]

# Cache: avoid reconnecting to Google Sheets on every call
_sheets_checked = False
_cached_worksheet = None


def reset_sheets_cache():
    """Reset the sheets cache so the next pipeline run retries the connection."""
    global _sheets_checked, _cached_worksheet
    _sheets_checked = False
    _cached_worksheet = None


def _get_google_sheet():
    """
    Connect to Google Sheets using service account credentials.
    Caches the connection to avoid repeated warnings and slow reconnects.
    Returns worksheet or None.
    """
    global _sheets_checked, _cached_worksheet

    # Return cached result (even if None) to avoid repeat warnings
    if _sheets_checked:
        return _cached_worksheet

    _sheets_checked = True

    try:
        import gspread
        from google.oauth2.service_account import Credentials

        creds_path = os.getenv("GOOGLE_SHEETS_CREDS_PATH", "./data/google_creds.json")
        sheet_name = os.getenv("GOOGLE_SHEET_NAME", "Internship Tracker")

        if not Path(creds_path).exists():
            logger.info(
                f"[Sheets] No Google creds at {creds_path} -- using local CSV fallback"
            )
            _cached_worksheet = None
            return None

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]

        creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
        client = gspread.authorize(creds)

        try:
            spreadsheet = client.open(sheet_name)
        except gspread.SpreadsheetNotFound:
            logger.info(f"[Sheets] Creating new spreadsheet: {sheet_name}")
            spreadsheet = client.create(sheet_name)

        worksheet = spreadsheet.sheet1

        existing = worksheet.get_all_values()
        if not existing:
            worksheet.append_row(CSV_HEADERS)
            logger.info("[Sheets] Added header row to empty sheet")

        _cached_worksheet = worksheet
        logger.info("[Sheets] Connected to Google Sheets successfully")
        return worksheet

    except ImportError:
        logger.info("[Sheets] gspread not installed -- using CSV fallback")
        _cached_worksheet = None
        return None
    except Exception as e:
        logger.info(f"[Sheets] Could not connect to Google Sheets: {e} -- using CSV fallback")
        _cached_worksheet = None
        return None


def _ensure_csv_fallback():
    """Create the CSV fallback file with headers if it doesn't exist."""
    CSV_FALLBACK_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not CSV_FALLBACK_PATH.exists():
        with open(CSV_FALLBACK_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADERS)
        logger.info(f"[Sheets] Created CSV fallback: {CSV_FALLBACK_PATH}")


def _log_to_csv(listing: dict, status: str, cover_note: str):
    """Append a row to the local CSV fallback file."""
    _ensure_csv_fallback()
    try:
        preview = cover_note[:100].replace("\n", " ").strip()
        if len(cover_note) > 100:
            preview += "..."

        row = [
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            listing.get("company", "Unknown"),
            listing.get("title", "N/A"),
            listing.get("location", "N/A"),
            listing.get("source", "N/A"),
            status,
            str(listing.get("score", "N/A")),
            listing.get("apply_url", "N/A"),
            preview,
        ]

        with open(CSV_FALLBACK_PATH, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(row)

    except Exception as e:
        logger.error(f"[Sheets] Failed to write to CSV: {e}")


def log_application(listing: dict, status: str, cover_note: str = ""):
    """
    Log an application to Google Sheets (or CSV fallback).
    """
    try:
        worksheet = _get_google_sheet()

        preview = ""
        if cover_note:
            preview = cover_note[:100].replace("\n", " ").strip()
            if len(cover_note) > 100:
                preview += "..."

        row = [
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            listing.get("company", "Unknown"),
            listing.get("title", "N/A"),
            listing.get("location", "N/A"),
            listing.get("source", "N/A"),
            status,
            str(listing.get("score", "N/A")),
            listing.get("apply_url", "N/A"),
            preview,
        ]

        if worksheet:
            worksheet.append_row(row, value_input_option="USER_ENTERED")
            logger.info(
                f"  Logged to Sheets: {listing.get('company')} -- {listing.get('title')} [{status}]"
            )
        else:
            _log_to_csv(listing, status, cover_note)

    except Exception as e:
        logger.warning(f"[Sheets] Failed to log: {e}")
        try:
            _log_to_csv(listing, status, cover_note)
        except Exception as csv_err:
            logger.error(f"[Sheets] CSV fallback also failed: {csv_err}")


def get_applied_urls() -> set:
    """
    Load all previously-applied URLs into a set (called once, cached by caller).
    Checks Google Sheets first, falls back to local CSV.
    """
    urls = set()

    # Try Google Sheets
    try:
        worksheet = _get_google_sheet()
        if worksheet:
            all_values = worksheet.get_all_values()
            for row in all_values[1:]:  # Skip header
                if len(row) > 7 and row[7].strip():
                    urls.add(row[7].strip())
            if urls:
                logger.info(f"[Sheets] Loaded {len(urls)} previously-applied URLs from Sheets")
            return urls
    except Exception as e:
        logger.debug(f"[Sheets] Could not load from Google Sheets: {e}")

    # Fallback: local CSV
    try:
        if CSV_FALLBACK_PATH.exists():
            with open(CSV_FALLBACK_PATH, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                next(reader, None)  # Skip header
                for row in reader:
                    if len(row) > 7 and row[7].strip():
                        urls.add(row[7].strip())
            if urls:
                logger.info(f"[Sheets] Loaded {len(urls)} previously-applied URLs from CSV")
    except Exception as e:
        logger.debug(f"[Sheets] Could not load from CSV: {e}")

    return urls


def already_applied(apply_url: str, applied_cache: set = None) -> bool:
    """
    Check if we've already applied to this URL.

    Args:
        apply_url:     The internship listing URL to check.
        applied_cache: Optional pre-loaded set of URLs (from get_applied_urls).

    Returns:
        True if already applied, False otherwise.
    """
    if not apply_url:
        return False

    if applied_cache is not None:
        return apply_url.strip() in applied_cache

    # Fallback: load fresh (slower, used if cache not provided)
    all_urls = get_applied_urls()
    return apply_url.strip() in all_urls
