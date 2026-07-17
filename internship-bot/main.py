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
from platforms.naukri import NaukriPlatform

from agent.filter import filter_listings
from agent.cover_note import generate_cover_note
from tracker.sheets import log_application, get_applied_urls, reset_sheets_cache
from notifier.telegram import send_summary as telegram_summary, send_instant as telegram_instant, send_document as telegram_document
from notifier.push import send_summary as ntfy_summary, send_instant as ntfy_instant
from notifier.whatsapp import send_summary as whatsapp_summary, send_instant as whatsapp_instant
from utils.dedup import deduplicate
from utils.browser import create_driver
from agent.interview_prep import generate_interview_prep
from platforms.login import LOGIN_HANDLERS
from agent.resume_brain import get_resume_context
from core.models import CandidateProfile, profile_from_dict

# ─── Constants ───
PROFILE_PATH = Path("./data/profile.json")
LOG_DIR = Path("./logs")
DATA_DIR = Path("./data")
SCHEDULE_TIME = "09:00"

# ─── Ensure required directories exist (safe for fresh clones) ───
for _d in (LOG_DIR, DATA_DIR):
    _d.mkdir(parents=True, exist_ok=True)

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
    """Load and validate profile.json via Pydantic. Returns a plain dict for
    backward compatibility, but validation ensures no silent KeyErrors."""
    if not PROFILE_PATH.exists():
        print(f"❌ Profile not found: {PROFILE_PATH}")
        sys.exit(1)

    with open(PROFILE_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)

    # Validate through Pydantic — raises ValidationError with clear messages
    try:
        validated = profile_from_dict(raw)
    except Exception as e:
        logging.getLogger("main").warning(f"⚠️  profile.json validation warning: {e}")
        validated = None

    profile = validated.model_dump(mode="python") if validated else raw

    # Runtime warnings
    _log = logging.getLogger("main")
    resume_path = profile.get("resume_path", "")
    if resume_path:
        if not Path(resume_path).exists():
            _log.warning(f"⚠️  resume_path '{resume_path}' does not exist! Resume uploads will fail.")
    else:
        _log.warning("⚠️  No resume_path set in profile.json — resume uploads will fail.")

    email = profile.get("email", "")
    if email in ("youremail@example.com", ""):
        _log.warning("⚠️  Email in profile.json is placeholder or empty! Logins may fail.")

    return profile

def validate_env(logger) -> None:
    dry_run = os.getenv("DRY_RUN", "true").lower() == "true"
    logger.info(f"🔒 DRY_RUN mode: {'ON — no real submissions' if dry_run else 'OFF — LIVE MODE'}")

    checks = [
        ("GEMINI_API_KEY", "your_gemini_key_here", "AI scoring disabled — using local keyword matching"),
        ("INTERNSHALA_EMAIL", None, "Internshala auto-apply disabled"),
        ("LINKEDIN_EMAIL", None, "LinkedIn scraper disabled"),
        ("NAUKRI_EMAIL", None, "Naukri auto-apply disabled"),
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

def run_pipeline(platform_filter: str = None):
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

    # 🔑 Reset AI key states for fresh run
    from agent.ai_client import reset_exhausted_keys
    reset_exhausted_keys()

    # 🧠 Initialize Resume Brain
    logger.info("\n" + "━" * 50)
    logger.info("🧠 STEP 0: Initializing AI Resume Brain…")
    logger.info("━" * 50)
    try:
        resume_ctx = get_resume_context()
        logger.info(f"  → Active Context: {resume_ctx.name}")
        logger.info(f"  → Extracted Skills: {len(resume_ctx.skills)}")
        logger.info(f"  → Extracted Projects: {len(resume_ctx.projects)}")
        
        # Sync profile.json
        if resume_ctx.name:
            profile["skills"] = resume_ctx.skills
            profile["projects"] = [
                f"{p.get('name')} ({', '.join(p.get('techs', []))})"
                for p in resume_ctx.projects
            ]
            if resume_ctx.achievements:
                profile["achievement"] = resume_ctx.achievements[0]
            with open(PROFILE_PATH, "w", encoding="utf-8") as f:
                json.dump(profile, f, indent=2, ensure_ascii=False)
            logger.info("  → Synced profile.json with Resume Brain data")
            
    except Exception as e:
        logger.error(f"  ✗ Resume Brain init failed: {e}")

    applied_listings: list[dict] = []
    manual_listings: list[dict] = []
    dry_run_listings: list[dict] = []
    skipped_count = 0
    error_count = 0

    platforms = {
        "internshala": InternshalaPlatform(),
        "linkedin": LinkedInPlatform(),
        "indeed": IndeedPlatform(),
        "unstop": UnstopPlatform(),
        "naukri": NaukriPlatform(),
        "generic_web": GenericWebPlatform(),
    }

    # PLATFORM LIMITS
    caps = {
        "internshala": int(os.getenv("INTERNSHALA_MAX_APPLIES", "15")),
        "linkedin": int(os.getenv("LINKEDIN_MAX_APPLIES", "10")),
        "indeed": int(os.getenv("INDEED_MAX_APPLIES", "10")),
        "unstop": int(os.getenv("UNSTOP_MAX_APPLIES", "15")),
        "naukri": int(os.getenv("NAUKRI_MAX_APPLIES", "15")),
        "generic_web": 20
    }
    platform_applied_counts = {k: 0 for k in platforms.keys()}

    # 1. SEARCH
    logger.info("\n" + "━" * 50)
    logger.info("📡 STEP 1: Scraping listings…")
    logger.info("━" * 50)

    all_listings: list[dict] = []
    for name, platform in platforms.items():
        # Skip platforms not matching the filter
        if platform_filter and name != platform_filter:
            continue
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
    
    # Login to platforms before applying
    is_dry_run = os.getenv("DRY_RUN", "false").lower() == "true"
    logged_in_platforms: set[str] = set()

    if not is_dry_run:
        logger.info("\n🔐 Logging into platforms...")
        for source_name in grouped.keys():
            login_fn = LOGIN_HANDLERS.get(source_name)
            if login_fn:
                try:
                    success = login_fn(driver)
                    if success:
                        logged_in_platforms.add(source_name)
                    else:
                        logger.warning(f"  ⚠️ Could not login to {source_name} — will skip its applications")
                except Exception as e:
                    logger.error(f"  ✗ Login to {source_name} crashed: {e}")
            else:
                # Platforms without login requirements (indeed, generic_web)
                logged_in_platforms.add(source_name)
    else:
        # In dry run mode, mark all platforms as "logged in" (they won't actually apply)
        logged_in_platforms = set(grouped.keys())

    try:
        for source_name, listings in grouped.items():
            platform = platforms.get(source_name)
            if not platform:
                continue

            # Skip platforms we couldn't log into (unless dry run)
            if source_name not in logged_in_platforms:
                logger.warning(f"  ⏭ Skipping {source_name} — not logged in")
                skipped_count += len(listings)
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
                    if "dry run" in msg:
                        # DRY RUN: do NOT count as real application
                        dry_run_listings.append(listing)
                        status = "Dry Run"
                        logger.info(f"  🧪 {result.get('message')}")
                    elif "manual" in msg or "pending" in msg:
                        manual_listings.append(listing)
                        status = "Pending (Manual)"
                        logger.info(f"  ✅ {result.get('message')}")
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
    if dry_run_listings:
        logger.info(f"  🧪 Dry Run: {len(dry_run_listings)} (not actually submitted)")
    logger.info(f"  ⏭  Skipped: {skipped_count}")
    logger.info(f"  ❌ Errors:  {error_count}")
    logger.info("=" * 60)

def debug_single_apply():
    """
    Debug mode: test the entire apply flow on a specific Internshala URL.
    Opens Chrome visually, takes screenshots at each step, and reports the result.
    Usage: python main.py --debug-apply "https://internshala.com/internship/detail/..."
    """
    import sys
    from agent.cover_note import generate_cover_note
    from applicator.selenium_fill import apply_internshala

    if len(sys.argv) > 2:
        url = sys.argv[2]
    else:
        url = input("Enter Internshala listing URL: ").strip()

    profile = load_profile()

    listing = {
        "title": "Debug Application",
        "company": "Debug Corp",
        "location": "Remote",
        "apply_url": url,
        "source": "internshala",
        "stipend": "N/A",
        "duration": "N/A",
    }

    print(f"\n🧪 DEBUG APPLY MODE")
    print(f"   URL: {url}")
    print(f"   Screenshots will be saved to: logs/screenshots/\n")

    cover = generate_cover_note(listing, profile)
    print(f"📝 Cover note preview (first 200 chars):\n{cover[:200]}...\n")

    result = apply_internshala(listing, cover, profile)

    print("\n" + "=" * 50)
    icon = "✅" if result["success"] else "❌"
    print(f"{icon} Result: {result['message']}")
    print(f"\n📸 Check screenshots in: logs/screenshots/")
    print("   Key screenshots to check:")
    print("   - 3_FAIL_no_apply_button.png → Apply button selector broken")
    print("   - 3_FAIL_login_wall.png      → Login session expired")
    print("   - 5_FAIL_no_submit_button.png → Submit button not found")
    print("   - 6_SUCCESS.png              → Application confirmed!")
    print("   - 6_UNCERTAIN.png            → Submitted but unconfirmed")
    print("=" * 50)


def test_scoring():
    """
    Runs a few sample listings through the AI scorer (filter.py) and prints the results
    without actually applying. Good for testing fine-tuned models.
    """
    import sys
    from agent.filter import filter_listings

    profile = load_profile()
    
    print("\n🧪 TESTING AI SCORER MODEL")
    print(f"   Using SCORER MODEL: {os.getenv('TUNED_SCORER_MODEL', os.getenv('GEMINI_MODEL', 'gemini-1.5-flash'))}")
    print("=" * 60)

    samples = [
        {"title": "Flutter Developer Intern", "company": "Groww", "description": "Looking for Flutter dev with Riverpod", "location": "Remote"},
        {"title": "React Frontend Intern", "company": "Razorpay", "description": "React, Next.js experience required.", "location": "Bengaluru"},
        {"title": "HR Intern", "company": "Big Corp", "description": "Help with recruiting and payroll", "location": "Remote"},
        {"title": "Data Science Intern", "company": "Analytics Co", "description": "Python, Pandas, Machine Learning", "location": "Pune"},
        {"title": "MERN Stack Developer", "company": "Startup", "description": "Node.js, Express, React, MongoDB", "location": "Remote"}
    ]

    for listing in samples:
        print(f"\nEvaluating: {listing['title']} @ {listing['company']}...")
        
    # filter_listings will automatically print the scores to the logger
    logger = logging.getLogger("main")
    logger.setLevel(logging.INFO)
    
    approved = filter_listings(samples, profile)
    
    print("\n" + "=" * 60)
    print(f"🏁 TEST COMPLETE. Approved {len(approved)} out of {len(samples)}.")
    print("=" * 60)
    sys.exit(0)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-now", action="store_true")
    parser.add_argument("--time", type=str, default=SCHEDULE_TIME)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--test-notify", action="store_true", help="Send a test notification to all channels")
    parser.add_argument("--test-scoring", action="store_true", help="Test the AI scorer against 5 sample listings")
    parser.add_argument("--debug-apply", action="store_true", help="Test apply flow on a single Internshala URL (pass URL as next arg)")
    parser.add_argument("--platform", type=str, default=None, help="Run only a specific platform (e.g., naukri, linkedin, internshala)")
    parser.add_argument("--schedule-file", type=str, default=None, help="Path to schedules.json for multi-platform scheduling")
    args = parser.parse_known_args()[0]  # allow extra positional for URL

    if args.debug_apply:
        setup_logging()
        debug_single_apply()
        return

    if args.test_scoring:
        setup_logging()
        test_scoring()
        return

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
        run_pipeline(platform_filter=args.platform)
    elif args.schedule_file:
        # Multi-platform scheduled sessions from schedules.json
        import schedule
        import time as time_module
        import json

        schedule_path = args.schedule_file
        logger.info(f"📅 Loading schedules from: {schedule_path}")

        try:
            with open(schedule_path, "r", encoding="utf-8") as f:
                schedules = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load schedules: {e}")
            sys.exit(1)

        day_map = {
            "daily": lambda job: job,
            "weekdays": lambda job: job.monday.at(job.at_time_str).do(job.job_func) if False else job,
        }

        for sched in schedules:
            if sched.get("enabled", True) is False:
                continue

            plat = sched.get("platform", "all")
            run_time = sched.get("time", "10:00")
            days = sched.get("days", "daily").lower()

            def make_job(p=plat):
                return lambda: run_pipeline(platform_filter=p if p != "all" else None)

            if days == "daily":
                schedule.every().day.at(run_time).do(make_job())
            elif days == "weekdays":
                for day_fn in [schedule.every().monday, schedule.every().tuesday,
                               schedule.every().wednesday, schedule.every().thursday,
                               schedule.every().friday]:
                    day_fn.at(run_time).do(make_job())
            elif days == "weekends":
                schedule.every().saturday.at(run_time).do(make_job())
                schedule.every().sunday.at(run_time).do(make_job())
            else:
                # Custom days like "mon,wed,fri"
                day_names = {
                    "mon": schedule.every().monday,
                    "tue": schedule.every().tuesday,
                    "wed": schedule.every().wednesday,
                    "thu": schedule.every().thursday,
                    "fri": schedule.every().friday,
                    "sat": schedule.every().saturday,
                    "sun": schedule.every().sunday,
                }
                for day_str in days.split(","):
                    day_str = day_str.strip().lower()[:3]
                    if day_str in day_names:
                        day_names[day_str].at(run_time).do(make_job())

            logger.info(f"  ✓ Scheduled: {plat} at {run_time} ({days})")

        logger.info(f"⏰ {len([s for s in schedules if s.get('enabled', True)])} schedule(s) active. Waiting...")

        try:
            while True:
                schedule.run_pending()
                time_module.sleep(30)
        except KeyboardInterrupt:
            logger.info("\n👋 Scheduler stopped by user. Goodbye!")
            sys.exit(0)
    else:
        import schedule
        import time

        logger.info(f"⏰ Scheduling daily run at {args.time}")
        schedule.every().day.at(args.time).do(lambda: run_pipeline(platform_filter=args.platform))

        try:
            while True:
                schedule.run_pending()
                time.sleep(60)
        except KeyboardInterrupt:
            logger.info("\n👋 Scheduler stopped by user. Goodbye!")
            sys.exit(0)

if __name__ == "__main__":
    main()
