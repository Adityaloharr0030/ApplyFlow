#!/usr/bin/env python3
"""
main.py — Internship Automation Bot
═══════════════════════════════════════════════════════════════
The main orchestrator that ties everything together:
  1. Scrapes internship listings from Internshala, LinkedIn, LetsInternship
  2. Deduplicates results across all sources
  3. Filters out already-applied listings
  4. Scores each listing with Claude AI
  5. Generates personalized cover notes for approved listings
  6. Auto-applies via Selenium (Internshala) or sends cold emails
  7. Logs everything to Google Sheets (with CSV fallback)
  8. Sends a Telegram summary

Usage:
  python main.py --run-now     Run the pipeline immediately (one shot)
  python main.py               Start the daily scheduler (runs at 9:00 AM)

Author: Aditya Lohar
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# ─── Load environment variables FIRST (before any other imports use them) ───
from dotenv import load_dotenv

load_dotenv()

# ─── Project imports ───
from scraper.internshala import scrape_internshala
from scraper.linkedin import scrape_linkedin
from scraper.letsinternship import scrape_letsinternship
from agent.filter import filter_listings
from agent.cover_note import generate_cover_note
from applicator.selenium_fill import apply_internshala, create_driver, login_internshala
from applicator.linkedin_fill import apply_linkedin, login_linkedin
from applicator.letsintern_fill import apply_letsinternship
from applicator.email_send import send_cold_email
from tracker.sheets import log_application, already_applied, get_applied_urls
from notifier.telegram import send_summary
from utils.dedup import deduplicate
from utils.dedup import deduplicate

# ─── Constants ───
PROFILE_PATH = Path("./data/profile.json")
LOG_DIR = Path("./logs")
SCHEDULE_TIME = "09:00"  # Daily run time (24h format)


def setup_logging() -> logging.Logger:
    """
    Configure logging to both console and a daily log file.
    Log file: ./logs/run_YYYY-MM-DD.log
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = LOG_DIR / f"run_{today}.log"

    # Create formatters
    file_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S",
    )

    # File handler (detailed, UTF-8)
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)

    # Console handler — force UTF-8 to avoid Windows cp1252 crashes with emoji
    import io
    utf8_stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    console_handler = logging.StreamHandler(utf8_stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    logger = logging.getLogger("main")
    logger.info(f"Logging to: {log_file}")
    return logger


def load_profile() -> dict:
    """
    Load the candidate profile from data/profile.json.
    Exits if the file is missing.
    """
    if not PROFILE_PATH.exists():
        print(f"❌ Profile not found: {PROFILE_PATH}")
        print("   Please create data/profile.json with your details.")
        sys.exit(1)

    with open(PROFILE_PATH, "r", encoding="utf-8") as f:
        profile = json.load(f)

    return profile


def run_pipeline():
    """
    Execute the full internship automation pipeline.
    This is the core function that runs all steps in sequence.
    """
    logger = logging.getLogger("main")

    # ═══════════════════════════════════════════════════════════
    #  SETUP
    # ═══════════════════════════════════════════════════════════
    logger.info("=" * 60)
    logger.info("🤖 INTERNSHIP AUTOMATION BOT — Starting pipeline")
    logger.info(f"📅 Date: {datetime.now().strftime('%A, %d %B %Y at %H:%M')}")
    logger.info("=" * 60)

    # Load candidate profile
    profile = load_profile()
    logger.info(f"👤 Candidate: {profile.get('name', 'Unknown')}")
    logger.info(f"🎓 {profile.get('degree', 'N/A')} — {profile.get('year', 'N/A')}")
    logger.info(f"🔑 Keywords: {', '.join(profile.get('keywords', []))}")

    # Tracking counters
    applied_listings: list[dict] = []
    skipped_count = 0
    error_count = 0

    # ═══════════════════════════════════════════════════════════
    #  STEP 1: SCRAPE ALL SOURCES
    # ═══════════════════════════════════════════════════════════
    logger.info("")
    logger.info("━" * 50)
    logger.info("📡 STEP 1: Scraping internship listings…")
    logger.info("━" * 50)

    all_listings: list[dict] = []

    # Internshala
    try:
        logger.info("\n🔍 [1/3] Scraping Internshala…")
        internshala_results = scrape_internshala(profile)
        all_listings.extend(internshala_results)
        logger.info(f"  → Got {len(internshala_results)} listing(s) from Internshala")
    except Exception as e:
        logger.error(f"  ✗ Internshala scraper crashed: {e}")
        error_count += 1

    # LinkedIn
    try:
        logger.info("\n🔍 [2/3] Scraping LinkedIn…")
        linkedin_results = scrape_linkedin(profile)
        all_listings.extend(linkedin_results)
        logger.info(f"  → Got {len(linkedin_results)} listing(s) from LinkedIn")
    except Exception as e:
        logger.error(f"  ✗ LinkedIn scraper crashed: {e}")
        error_count += 1

    # LetsInternship
    try:
        logger.info("\n🔍 [3/3] Scraping LetsInternship…")
        letsintern_results = scrape_letsinternship(profile)
        all_listings.extend(letsintern_results)
        logger.info(f"  → Got {len(letsintern_results)} listing(s) from LetsInternship")
    except Exception as e:
        logger.error(f"  ✗ LetsInternship scraper crashed: {e}")
        error_count += 1

    logger.info(f"\n📊 Total raw listings: {len(all_listings)}")

    if not all_listings:
        logger.warning("⚠️ No listings found from any source — ending pipeline early")
        send_summary(applied_listings, skipped_count, error_count)
        return

    # ═══════════════════════════════════════════════════════════
    #  STEP 2: DEDUPLICATE
    # ═══════════════════════════════════════════════════════════
    logger.info("")
    logger.info("━" * 50)
    logger.info("♻️  STEP 2: Deduplicating listings…")
    logger.info("━" * 50)

    unique_listings = deduplicate(all_listings)
    dupes_removed = len(all_listings) - len(unique_listings)
    if dupes_removed > 0:
        logger.info(f"  Removed {dupes_removed} duplicate(s)")

    # ═══════════════════════════════════════════════════════════
    #  STEP 3: FILTER ALREADY-APPLIED
    # ═══════════════════════════════════════════════════════════
    logger.info("")
    logger.info("━" * 50)
    logger.info("🔎 STEP 3: Filtering already-applied listings…")
    logger.info("━" * 50)

    new_listings: list[dict] = []
    applied_cache = get_applied_urls()  # Load all URLs once (not per-listing)
    for listing in unique_listings:
        url = listing.get("apply_url", "")
        if url and url.strip() in applied_cache:
            logger.info(f"  SKIP Already applied: {listing.get('title')} @ {listing.get('company')}")
            skipped_count += 1
        else:
            new_listings.append(listing)

    logger.info(f"  → {len(new_listings)} new listing(s) to evaluate")

    if not new_listings:
        logger.info("✅ All listings already applied to — nothing new today")
        send_summary(applied_listings, skipped_count, error_count)
        return

    # ═══════════════════════════════════════════════════════════
    #  STEP 4: AI SCORING
    # ═══════════════════════════════════════════════════════════
    logger.info("")
    logger.info("━" * 50)
    logger.info("🧠 STEP 4: Scoring listings with Claude AI…")
    logger.info("━" * 50)

    try:
        approved_listings = filter_listings(new_listings, profile)
        skipped_count += len(new_listings) - len(approved_listings)
    except Exception as e:
        logger.error(f"  ✗ AI filter crashed: {e}")
        error_count += 1
        approved_listings = []

    logger.info(f"  → {len(approved_listings)} listing(s) approved for application")

    if not approved_listings:
        logger.info("ℹ️ No listings scored high enough to apply — done for today")
        send_summary(applied_listings, skipped_count, error_count)
        return

    # ═══════════════════════════════════════════════════════════
    #  STEP 5: APPLY TO EACH APPROVED LISTING
    # ═══════════════════════════════════════════════════════════
    logger.info("")
    logger.info("━" * 50)
    logger.info("🚀 STEP 5: Applying to approved listings…")
    logger.info("━" * 50)

    # Check what platforms we need to log into
    needs_internshala = any(l.get("source") == "internshala" for l in approved_listings)
    needs_linkedin = any(l.get("source") == "linkedin" for l in approved_listings)
    
    driver = None
    try:
        logger.info("  🌐 Initializing persistent Chrome session...")
        driver = create_driver()
        if not driver:
            logger.error("  ✗ Failed to initialize Chrome driver. Aborting auto-apply.")
            return

        if needs_internshala:
            if not login_internshala(driver):
                logger.error("  ✗ Internshala login failed. Will skip those listings.")
                needs_internshala = False
                
        if needs_linkedin:
            if not login_linkedin(driver):
                logger.error("  ✗ LinkedIn login failed. Will skip those listings.")
                needs_linkedin = False

        for i, listing in enumerate(approved_listings, 1):
            company = listing.get("company", "Unknown")
            title = listing.get("title", "N/A")
            source = listing.get("source", "unknown")

            logger.info(f"\n── [{i}/{len(approved_listings)}] {title} @ {company} ({source}) ──")

            # Step 5a: Generate cover note
            try:
                logger.info("  ✍️  Generating cover note…")
                cover_note = generate_cover_note(listing, profile)
            except Exception as e:
                logger.error(f"  ✗ Cover note generation failed: {e}")
                cover_note = ""
                error_count += 1

            # Step 5b: Apply based on source
            application_result = {"success": False, "message": "Not attempted"}

            if source == "internshala":
                if not needs_internshala:
                    application_result = {"success": False, "message": "Login failed previously"}
                else:
                    try:
                        logger.info("  🖱️ Auto-filling Internshala application…")
                        application_result = apply_internshala(driver, listing, cover_note, profile)
                    except Exception as e:
                        logger.error(f"  ✗ Selenium application failed: {e}")
                        application_result = {"success": False, "message": str(e)}

            elif source == "linkedin":
                if not needs_linkedin:
                    application_result = {"success": False, "message": "Login failed previously"}
                else:
                    try:
                        logger.info("  🖱️ Auto-filling LinkedIn Easy Apply…")
                        application_result = apply_linkedin(driver, listing, cover_note, profile)
                    except Exception as e:
                        logger.error(f"  ✗ Selenium application failed: {e}")
                        application_result = {"success": False, "message": str(e)}

            elif source == "letsinternship":
                try:
                    logger.info("  🖱️ Auto-filling LetsInternship application…")
                    application_result = apply_letsinternship(driver, listing, cover_note, profile)
                except Exception as e:
                    logger.error(f"  ✗ Selenium application failed: {e}")
                    application_result = {"success": False, "message": str(e)}

            # Step 5c: Log the result
            if application_result.get("success"):
                status = "Applied" if "manual" not in application_result.get("message", "").lower() else "Pending (Manual)"
                applied_listings.append(listing)
                logger.info(f"  ✅ {application_result.get('message')}")
            else:
                status = f"Error: {application_result.get('message')}"
                error_count += 1
                logger.warning(f"  ✗ {application_result.get('message')}")

            # Log to tracker (Google Sheets / CSV)
            try:
                log_application(listing, status, cover_note)
            except Exception as e:
                logger.error(f"  ✗ Failed to log application: {e}")

    finally:
        if driver:
            try:
                logger.info("  🛑 Closing Chrome session...")
                driver.quit()
            except Exception:
                pass

    # ═══════════════════════════════════════════════════════════
    #  STEP 6: SEND TELEGRAM SUMMARY
    # ═══════════════════════════════════════════════════════════
    logger.info("")
    logger.info("━" * 50)
    logger.info("📱 STEP 6: Sending Telegram summary…")
    logger.info("━" * 50)

    try:
        send_summary(applied_listings, skipped_count, error_count)
    except Exception as e:
        logger.error(f"  ✗ Telegram notification failed: {e}")

    # ═══════════════════════════════════════════════════════════
    #  SUMMARY
    # ═══════════════════════════════════════════════════════════
    logger.info("")
    logger.info("=" * 60)
    logger.info("🏁 PIPELINE COMPLETE")
    logger.info(f"  ✅ Applied: {len(applied_listings)}")
    logger.info(f"  ⏭  Skipped: {skipped_count}")
    logger.info(f"  ❌ Errors:  {error_count}")
    logger.info("=" * 60)


def main():
    """
    Entry point — handles CLI arguments and scheduling.
    """
    parser = argparse.ArgumentParser(
        description="🤖 Internship Automation Bot — Auto-apply to internships daily",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --run-now     Run the full pipeline immediately
  python main.py               Start the daily scheduler (9:00 AM)
  python main.py --time 10:30  Schedule daily at 10:30 AM
        """,
    )
    parser.add_argument(
        "--run-now",
        action="store_true",
        help="Run the pipeline immediately (one-shot, no scheduling)",
    )
    parser.add_argument(
        "--time",
        type=str,
        default=SCHEDULE_TIME,
        help=f"Daily schedule time in HH:MM format (default: {SCHEDULE_TIME})",
    )
    args = parser.parse_args()

    # Setup logging
    logger = setup_logging()

    if args.run_now:
        # ─── ONE-SHOT RUN ───
        logger.info("🚀 Running in one-shot mode (--run-now)")
        run_pipeline()
    else:
        # ─── DAILY SCHEDULER ───
        import schedule
        import time

        logger.info(f"⏰ Scheduling daily run at {args.time}")
        logger.info("   Press Ctrl+C to stop the scheduler")
        logger.info(f"   Tip: use 'python main.py --run-now' for immediate execution")

        schedule.every().day.at(args.time).do(run_pipeline)

        # Also show when the next run is
        logger.info(f"   Next run: {args.time} tomorrow")
        logger.info("")

        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            logger.info("\n👋 Scheduler stopped by user. Goodbye!")
            sys.exit(0)


if __name__ == "__main__":
    main()
