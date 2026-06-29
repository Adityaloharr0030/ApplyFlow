#!/usr/bin/env python3
"""
main.py — Internship Automation Bot
═══════════════════════════════════════════════════════════════
Orchestrator for the ApplyFlow bot.
Supports: Internshala, LinkedIn, Indeed, Unstop, and Cold Email.
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from collections import defaultdict

# ─── Load environment variables FIRST ───
from dotenv import load_dotenv
load_dotenv()

# ─── Project imports ───
from platforms.internshala import InternshalaPlatform
from platforms.linkedin import LinkedInPlatform
from platforms.indeed import IndeedPlatform
from platforms.unstop import UnstopPlatform
from platforms.generic_web import GenericWebPlatform

from agent.filter import filter_listings
from agent.cover_note import generate_cover_note
from tracker.sheets import log_application, get_applied_urls, reset_sheets_cache
from notifier.telegram import send_summary as telegram_summary, send_instant as telegram_instant, send_document as telegram_document
from notifier.push import send_summary as ntfy_summary, send_instant as ntfy_instant
from notifier.whatsapp import send_summary as whatsapp_summary, send_instant as whatsapp_instant
from utils.dedup import deduplicate
from utils.browser import create_driver
from agent.interview_prep import generate_interview_prep

# ─── Constants ───
PROFILE_PATH = Path("./data/profile.json")
LOG_DIR = Path("./logs")
SCHEDULE_TIME = "09:00"

def setup_logging() -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = LOG_DIR / f"run_{today}.log"

    file_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S",
    )

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)

    import io
    utf8_stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    console_handler = logging.StreamHandler(utf8_stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    logger = logging.getLogger("main")
    logger.info(f"Logging to: {log_file}")
    return logger

def load_profile() -> dict:
    if not PROFILE_PATH.exists():
        print(f"❌ Profile not found: {PROFILE_PATH}")
        sys.exit(1)

    with open(PROFILE_PATH, "r", encoding="utf-8") as f:
        profile = json.load(f)

    # Validate resume_path exists
    resume_path = profile.get("resume_path", "")
    if resume_path:
        rp = Path(resume_path)
        if not rp.exists():
            logging.getLogger("main").warning(
                f"⚠️  resume_path '{resume_path}' does not exist! "
                "Applications that require a resume upload will fail."
            )
    else:
        logging.getLogger("main").warning(
            "⚠️  No resume_path set in profile.json — resume uploads will fail."
        )

    # Validate email isn't a placeholder
    email = profile.get("email", "")
    if email == "youremail@example.com" or not email:
        logging.getLogger("main").warning(
            "⚠️  Email in profile.json is a placeholder or empty! Cold emails/logins may fail."
        )

    return profile

def validate_env(logger) -> None:
    dry_run = os.getenv("DRY_RUN", "true").lower() == "true"
    logger.info(f"🔒 DRY_RUN mode: {'ON — no real submissions' if dry_run else 'OFF — LIVE MODE'}")

    checks = [
        ("GEMINI_API_KEY", "your_gemini_key_here", "AI scoring disabled — using local keyword matching"),
        ("INTERNSHALA_EMAIL", None, "Internshala auto-apply disabled"),
        ("LINKEDIN_EMAIL", None, "LinkedIn scraper disabled"),
        ("TELEGRAM_BOT_TOKEN", "your_bot_token_here", "Telegram notifications disabled"),
        ("GMAIL_ADDRESS", None, "Cold email disabled"),
    ]
    for key, placeholder, msg in checks:
        val = os.getenv(key, "")
        if not val or val == placeholder:
            logger.warning(f"⚠️  {key} not configured — {msg}")

def fire_instant_notification(platform_name: str, listing: dict, is_error: bool = False, error_msg: str = ""):
    if is_error:
        msg = f"⚠️ {platform_name.capitalize()} error: {error_msg}"
        tags = "warning"
    else:
        title = listing.get('title', 'Role')
        company = listing.get('company', 'Company')
        location = listing.get('location', 'Not specified')
        score = listing.get('score', '?')
        reason = listing.get('reason', 'N/A')
        url = listing.get('apply_url', '')
        
        msg = (
            f"✅ APPLIED: {title}\n"
            f"🏢 Company: {company}\n"
            f"📍 Location: {location}\n"
            f"🌐 Platform: {platform_name.capitalize()}\n"
            f"🎯 AI Score: {score}/10\n"
            f"💡 Why: {reason}\n"
            f"🔗 Link: {url}"
        )
        tags = "rocket"

    try:
        telegram_instant(msg)
    except Exception as e:
        logging.getLogger("main").warning(f"Telegram instant failed: {e}")
        
    try:
        ntfy_instant(msg, tags=tags)
    except Exception as e:
        logging.getLogger("main").warning(f"Ntfy instant failed: {e}")

    try:
        whatsapp_instant(msg)
    except Exception as e:
        logging.getLogger("main").warning(f"WhatsApp instant failed: {e}")

def send_summary(applied: list, skipped: int, errors: int, manual: list = None):
    logger = logging.getLogger("main")
    if manual is None:
        manual = []
    try:
        telegram_summary(applied, skipped, errors, manual)
        telegram_document("logs/applications.csv")
    except Exception as e:
        logger.error(f"  ✗ Telegram notification failed: {e}")
        
    try:
        ntfy_summary(applied, skipped, errors, manual)
    except Exception as e:
        logger.error(f"  ✗ Ntfy notification failed: {e}")

    try:
        whatsapp_summary(applied, skipped, errors, manual)
    except Exception as e:
        logger.error(f"  ✗ WhatsApp notification failed: {e}")

def run_pipeline():
    logger = logging.getLogger("main")

    logger.info("=" * 60)
    logger.info("🤖 INTERNSHIP AUTOMATION BOT — Starting pipeline")
    logger.info(f"📅 Date: {datetime.now().strftime('%A, %d %B %Y at %H:%M')}")
    logger.info("=" * 60)
    
    # Reset sheets cache so we re-try the connection if it failed previously
    reset_sheets_cache()

    profile = load_profile()
    validate_env(logger)
    logger.info(f"👤 Candidate: {profile.get('name', 'Unknown')}")
    logger.info(f"🔑 Keywords: {', '.join(profile.get('keywords', []))}")

    applied_listings: list[dict] = []
    manual_listings: list[dict] = []
    skipped_count = 0
    error_count = 0

    platforms = {
        "internshala": InternshalaPlatform(),
        "linkedin": LinkedInPlatform(),
        "indeed": IndeedPlatform(),
        "unstop": UnstopPlatform(),
        "generic_web": GenericWebPlatform(),
    }

    # PLATFORM LIMITS
    caps = {
        "internshala": int(os.getenv("INTERNSHALA_MAX_APPLIES", "15")),
        "linkedin": int(os.getenv("LINKEDIN_MAX_APPLIES", "10")),
        "indeed": int(os.getenv("INDEED_MAX_APPLIES", "10")),
        "unstop": int(os.getenv("UNSTOP_MAX_APPLIES", "15")),
        "generic_web": 20
    }
    platform_applied_counts = {k: 0 for k in platforms.keys()}

    # 1. SEARCH
    logger.info("\n" + "━" * 50)
    logger.info("📡 STEP 1: Scraping listings…")
    logger.info("━" * 50)

    all_listings: list[dict] = []
    for name, platform in platforms.items():
        try:
            logger.info(f"\n🔍 Scraping {name.capitalize()}…")
            results = platform.search(profile)
            all_listings.extend(results)
            logger.info(f"  → Got {len(results)} listing(s) from {name.capitalize()}")
        except Exception as e:
            logger.error(f"  ✗ {name.capitalize()} scraper crashed: {e}")
            error_count += 1

    logger.info(f"\n📊 Total raw listings: {len(all_listings)}")

    if not all_listings:
        logger.warning("⚠️ No listings found — ending pipeline early")
        send_summary(applied_listings, skipped_count, error_count)
        return

    # 2. DEDUPLICATE
    logger.info("\n" + "━" * 50)
    logger.info("♻️  STEP 2: Deduplicating listings…")
    logger.info("━" * 50)
    unique_listings = deduplicate(all_listings)
    dupes = len(all_listings) - len(unique_listings)
    if dupes > 0:
        logger.info(f"  Removed {dupes} duplicate(s)")
    logger.info(f"  → {len(unique_listings)} unique listing(s)")

    # 3. FILTER ALREADY APPLIED
    logger.info("\n" + "━" * 50)
    logger.info("🔎 STEP 3: Filtering already-applied listings…")
    logger.info("━" * 50)
    new_listings: list[dict] = []
    applied_cache = get_applied_urls()
    for listing in unique_listings:
        url = listing.get("apply_url", "")
        if url and url.strip() in applied_cache:
            skipped_count += 1
        else:
            new_listings.append(listing)
    logger.info(f"  → {len(new_listings)} new listing(s) to evaluate")

    if not new_listings:
        logger.info("✅ All listings already applied to — nothing new today")
        send_summary(applied_listings, skipped_count, error_count, manual_listings)
        return

    # 4. AI SCORING
    logger.info("\n" + "━" * 50)
    logger.info("🧠 STEP 4: Scoring listings…")
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
        send_summary(applied_listings, skipped_count, error_count, manual_listings)
        return

    # Group by platform to reuse driver per platform efficiently
    grouped = defaultdict(list)
    for listing in approved_listings:
        grouped[listing.get("source")].append(listing)

    # 5. APPLY
    logger.info("\n" + "━" * 50)
    logger.info("🚀 STEP 5: Applying to approved listings…")
    logger.info("━" * 50)

    driver = create_driver()
    if driver is None:
        logger.error("  ✗ CRITICAL ERROR: Failed to launch Chrome browser. Aborting apply phase.")
        logger.error("  💡 Tip: Make sure Chrome is installed and fully closed before running.")
        send_summary(applied_listings, skipped_count, error_count, manual_listings)
        return
    
    try:
        for source_name, listings in grouped.items():
            platform = platforms.get(source_name)
            if not platform:
                continue

            for listing in listings:
                if platform.check_circuit_breaker():
                    logger.warning(f"  ⚠️ Skipping {source_name} due to circuit breaker")
                    fire_instant_notification(source_name, listing, True, "Circuit breaker tripped (blocked).")
                    break

                if platform_applied_counts[source_name] >= caps.get(source_name, 10):
                    logger.info(f"  🛑 Daily cap reached for {source_name} ({caps.get(source_name)})")
                    break

                company = listing.get("company", "Unknown")
                title = listing.get("title", "N/A")
                logger.info(f"\n── {title} @ {company} ({source_name}) ──")

                try:
                    cover_note = generate_cover_note(listing, profile)
                except Exception as e:
                    logger.error(f"  ✗ Cover note generation failed: {e}")
                    cover_note = ""

                try:
                    result = platform.apply(listing, cover_note, profile, driver)
                except Exception as e:
                    result = {"success": False, "message": str(e)}

                if result.get("success"):
                    msg = result.get("message", "").lower()
                    if "manual" in msg or "pending" in msg:
                        manual_listings.append(listing)
                        status = "Pending (Manual)"
                    else:
                        applied_listings.append(listing)
                        status = "Applied"
                        platform_applied_counts[source_name] += 1
                        fire_instant_notification(source_name, listing)
                        # Generate interview prep asynchronously or in background
                        try:
                            generate_interview_prep(listing, profile)
                        except Exception as prep_e:
                            logger.error(f"  ✗ Interview prep generation failed: {prep_e}")
                    logger.info(f"  ✅ {result.get('message')}")
                else:
                    status = f"Error: {result.get('message')}"
                    error_count += 1
                    logger.warning(f"  ✗ {result.get('message')}")
                    
                    if "captcha" in status.lower() or "blocked" in status.lower():
                        fire_instant_notification(source_name, listing, True, result.get('message'))

                try:
                    log_application(listing, status, cover_note)
                except Exception as e:
                    logger.error(f"  ✗ Failed to log application: {e}")

    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

    # 6. SUMMARY
    logger.info("\n" + "━" * 50)
    logger.info("📱 STEP 6: Sending summary notifications…")
    logger.info("━" * 50)
    send_summary(applied_listings, skipped_count, error_count, manual_listings)

    logger.info("\n" + "=" * 60)
    logger.info("🏁 PIPELINE COMPLETE")
    logger.info(f"  ✅ Applied: {len(applied_listings)}")
    logger.info(f"  ⏭  Skipped: {skipped_count}")
    logger.info(f"  ❌ Errors:  {error_count}")
    logger.info("=" * 60)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-now", action="store_true")
    parser.add_argument("--time", type=str, default=SCHEDULE_TIME)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--test-notify", action="store_true", help="Send a test notification to all channels")
    args = parser.parse_args()

    if args.test_notify:
        logger = setup_logging()
        logger.info("🧪 Testing notifications...")
        dummy_applied = [{"company": "Test Company", "title": "Test Role"}]
        
        logger.info("-> Testing Telegram...")
        try:
            telegram_summary(dummy_applied, 0, 0)
        except Exception as e:
            logger.error(f"Telegram failed: {e}")
            
        logger.info("-> Testing Ntfy...")
        try:
            ntfy_summary(dummy_applied, 0, 0)
        except Exception as e:
            logger.error(f"Ntfy failed: {e}")
            
        logger.info("-> Testing WhatsApp...")
        try:
            whatsapp_summary(dummy_applied, 0, 0)
        except Exception as e:
            logger.error(f"WhatsApp failed: {e}")
            
        logger.info("Test complete.")
        sys.exit(0)

    if args.dry_run:
        os.environ["DRY_RUN"] = "true"

    logger = setup_logging()

    if args.run_now:
        logger.info("🚀 Running in one-shot mode (--run-now)")
        run_pipeline()
    else:
        import schedule
        import time

        logger.info(f"⏰ Scheduling daily run at {args.time}")
        schedule.every().day.at(args.time).do(run_pipeline)

        try:
            while True:
                schedule.run_pending()
                time.sleep(60)
        except KeyboardInterrupt:
            logger.info("\n👋 Scheduler stopped by user. Goodbye!")
            sys.exit(0)

if __name__ == "__main__":
    main()
