#!/usr/bin/env python3
"""
preflight_check.py — ApplyFlow Bot Health Check
═══════════════════════════════════════════════════
Runs a full checklist of every component to make sure the bot is ready to go.
"""

import os
import sys
import json
import importlib
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ─── Formatting Helpers ───
PASS = "  [PASS]"
FAIL = "  [FAIL]"
WARN = "  [WARN]"
INFO = "  [INFO]"

results = {"pass": 0, "fail": 0, "warn": 0}

def check(label, condition, fail_msg="", warn=False):
    if condition:
        print(f"{PASS} {label}")
        results["pass"] += 1
        return True
    else:
        if warn:
            print(f"{WARN} {label} — {fail_msg}")
            results["warn"] += 1
        else:
            print(f"{FAIL} {label} — {fail_msg}")
            results["fail"] += 1
        return False


def main():
    print("=" * 60)
    print("  ApplyFlow Bot — Preflight Health Check")
    print("=" * 60)

    # ═══════════════════════════════════════════════════════════
    # 1. ENVIRONMENT FILE
    # ═══════════════════════════════════════════════════════════
    print("\n--- 1. Environment File (.env) ---")
    env_path = Path(".env")
    check(".env file exists", env_path.exists(), "Missing .env file! Copy .env.example to .env")

    # ═══════════════════════════════════════════════════════════
    # 2. GEMINI AI API KEY
    # ═══════════════════════════════════════════════════════════
    print("\n--- 2. AI Brain (Anthropic / Gemini) ---")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
    gemini_key = os.getenv("GEMINI_API_KEY", "")

    has_anthropic = bool(anthropic_key) and anthropic_key != "your_key_here"
    has_gemini = bool(gemini_key) and gemini_key != "your_gemini_key_here"

    check("ANTHROPIC_API_KEY is set", has_anthropic, "Missing Claude API key (optional)", warn=True)
    check("GEMINI_API_KEY is set", has_gemini, "Missing Gemini API key", warn=not has_anthropic)

    if not has_anthropic and not has_gemini:
        check("Any AI API Key", False, "No valid AI keys found. Bot will use local keyword scoring.", warn=True)

    if has_anthropic:
        try:
            from anthropic import Anthropic
            client = Anthropic(api_key=anthropic_key)
            msg = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=10,
                messages=[{"role": "user", "content": "Say hello in one word."}]
            )
            resp_text = msg.content[0].text.strip()
            check("Anthropic API responds", True)
            print(f"{INFO} Claude replied: \"{resp_text}\"")
        except Exception as e:
            check("Anthropic API connection", False, f"Error: {e}", warn=True)
    elif has_gemini:
        try:
            from google import genai as google_genai
            from google.genai import types as genai_types
            client = google_genai.Client(api_key=gemini_key)
            model = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
            response = client.models.generate_content(
                model=model,
                contents="Say hello in one word.",
                config=genai_types.GenerateContentConfig(max_output_tokens=256)
            )
            resp_text = ""
            try:
                resp_text = (response.text or "").strip()
            except Exception:
                pass
            if not resp_text:
                try:
                    if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                        resp_text = response.candidates[0].content.parts[0].text.strip()
                except Exception:
                    pass

            if resp_text:
                check(f"Gemini API responds (model={model})", True)
                print(f"{INFO} Gemini replied: \"{resp_text}\"")
            else:
                check(f"Gemini API responds (model={model})", False,
                      "API connected but returned empty — bot will use local scoring fallback", warn=True)
        except Exception as e:
            err = str(e)
            if "429" in err or "quota" in err.lower():
                check("Gemini API quota", False, "QUOTA EXHAUSTED — bot will use local scoring fallback", warn=True)
            else:
                check("Gemini API connection", False, f"Error: {err} — bot will use local scoring fallback", warn=True)

    # ═══════════════════════════════════════════════════════════
    # 3. PROFILE DATA
    # ═══════════════════════════════════════════════════════════
    print("\n--- 3. Profile Data ---")
    profile_path = Path("./data/profile.json")
    check("profile.json exists", profile_path.exists(), "Missing data/profile.json!")

    profile = {}
    if profile_path.exists():
        with open(profile_path) as f:
            profile = json.load(f)
        check("Name is set", bool(profile.get("name")), "Missing 'name' in profile.json")
        check("Degree is set", bool(profile.get("degree")), "Missing 'degree' in profile.json")
        check("Skills list (>0)", len(profile.get("skills", [])) > 0, "No skills defined!")
        check("Keywords list (>0)", len(profile.get("keywords", [])) > 0, "No keywords defined!")
        check("Location prefs (>0)", len(profile.get("location_preferences", [])) > 0, "No location preferences!")
        print(f"{INFO} Skills: {', '.join(profile.get('skills', []))}")
        print(f"{INFO} Keywords: {', '.join(profile.get('keywords', []))}")

    resume_path = Path(profile.get("resume_path", "./data/resume.pdf"))
    check("Resume PDF exists", resume_path.exists(), f"Missing {resume_path}")

    # ═══════════════════════════════════════════════════════════
    # 4. PLATFORM LOGINS
    # ═══════════════════════════════════════════════════════════
    print("\n--- 4. Platform Login Credentials ---")

    internshala_email = os.getenv("INTERNSHALA_EMAIL", "")
    check("Internshala email", bool(internshala_email) and "@" in internshala_email,
          "Missing or invalid INTERNSHALA_EMAIL")
    check("Internshala password", bool(os.getenv("INTERNSHALA_PASSWORD", "")),
          "Missing INTERNSHALA_PASSWORD")

    linkedin_email = os.getenv("LINKEDIN_EMAIL", "")
    has_at = "@" in linkedin_email if linkedin_email else False
    check("LinkedIn email", bool(linkedin_email) and has_at,
          f"LINKEDIN_EMAIL='{linkedin_email}' — missing @ symbol!" if linkedin_email else "Missing LINKEDIN_EMAIL")
    check("LinkedIn password", bool(os.getenv("LINKEDIN_PASSWORD", "")),
          "Missing LINKEDIN_PASSWORD")

    unstop_email = os.getenv("UNSTOP_EMAIL", "")
    check("Unstop email", bool(unstop_email) and "@" in unstop_email,
          "Missing or invalid UNSTOP_EMAIL")
    check("Unstop password", bool(os.getenv("UNSTOP_PASSWORD", "")),
          "Missing UNSTOP_PASSWORD")

    # ═══════════════════════════════════════════════════════════
    # 5. NOTIFICATIONS
    # ═══════════════════════════════════════════════════════════
    print("\n--- 5. Notification Channels ---")

    tg_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    tg_chat = os.getenv("TELEGRAM_CHAT_ID", "")
    check("Telegram Bot Token", bool(tg_token) and ":" in tg_token, "Missing TELEGRAM_BOT_TOKEN")
    check("Telegram Chat ID", bool(tg_chat) and tg_chat.isdigit(), "Missing or invalid TELEGRAM_CHAT_ID")

    if tg_token and tg_chat:
        try:
            import requests
            resp = requests.get(f"https://api.telegram.org/bot{tg_token}/getMe", timeout=10)
            data = resp.json()
            if data.get("ok"):
                bot_name = data["result"].get("username", "?")
                check(f"Telegram bot alive (@{bot_name})", True)
            else:
                check("Telegram bot alive", False, f"API error: {data.get('description')}")
        except Exception as e:
            check("Telegram bot alive", False, f"Connection error: {e}")

    ntfy_topic = os.getenv("NTFY_TOPIC", "")
    check("Ntfy.sh topic", bool(ntfy_topic), "Missing NTFY_TOPIC", warn=True)

    wa_phone = os.getenv("WHATSAPP_PHONE", "")
    check("WhatsApp configured", bool(wa_phone) and wa_phone != "your_phone_here",
          "WhatsApp not configured (optional)", warn=True)

    # ═══════════════════════════════════════════════════════════
    # 6. PYTHON DEPENDENCIES
    # ═══════════════════════════════════════════════════════════
    print("\n--- 6. Python Dependencies ---")

    critical_packages = {
        "dotenv": "python-dotenv",
        "selenium": "selenium",
        "undetected_chromedriver": "undetected-chromedriver",
        "requests": "requests",
        "bs4": "beautifulsoup4",
        "google.genai": "google-genai",
        "anthropic": "anthropic",
    }
    optional_packages = {
        "jobspy": "python-jobspy",
        "streamlit": "streamlit",
        "schedule": "schedule",
    }

    for module, pip_name in critical_packages.items():
        try:
            importlib.import_module(module)
            check(f"{pip_name}", True)
        except ImportError:
            check(f"{pip_name}", False, f"pip install {pip_name}")

    for module, pip_name in optional_packages.items():
        try:
            importlib.import_module(module)
            check(f"{pip_name} (optional)", True)
        except ImportError:
            check(f"{pip_name} (optional)", False, f"pip install {pip_name}", warn=True)

    # ═══════════════════════════════════════════════════════════
    # 7. CHROME BROWSER
    # ═══════════════════════════════════════════════════════════
    print("\n--- 7. Chrome Browser ---")

    import subprocess
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    ]
    chrome_found = any(Path(p).exists() for p in chrome_paths)
    check("Chrome is installed", chrome_found, "Chrome not found in standard paths!")

    if chrome_found:
        try:
            chrome_exe = next(p for p in chrome_paths if Path(p).exists())
            result = subprocess.run([chrome_exe, "--version"], capture_output=True, text=True, timeout=10)
            version = result.stdout.strip()
            print(f"{INFO} Chrome version: {version}")
        except Exception:
            print(f"{INFO} Chrome found but could not detect version")

    bot_profile = Path(r"C:\ApplyFlow\bot_chrome_profile")
    check("Bot Chrome profile dir", bot_profile.exists(),
          "Missing bot_chrome_profile — run setup_profile.py first!")

    headless = os.getenv("HEADLESS", "true")
    print(f"{INFO} HEADLESS mode: {headless}")

    # ═══════════════════════════════════════════════════════════
    # 8. PLATFORM SCRAPERS
    # ═══════════════════════════════════════════════════════════
    print("\n--- 8. Platform Scrapers ---")

    platforms_ok = []
    try:
        from platforms.internshala import InternshalaPlatform
        check("Internshala scraper loads", True)
        platforms_ok.append("internshala")
    except Exception as e:
        check("Internshala scraper loads", False, str(e))

    try:
        from platforms.linkedin import LinkedInPlatform
        check("LinkedIn scraper loads", True)
        platforms_ok.append("linkedin")
    except Exception as e:
        check("LinkedIn scraper loads", False, str(e))

    try:
        from platforms.indeed import IndeedPlatform
        check("Indeed scraper loads", True)
        platforms_ok.append("indeed")
    except Exception as e:
        check("Indeed scraper loads", False, str(e))

    try:
        from platforms.unstop import UnstopPlatform
        check("Unstop scraper loads", True)
        platforms_ok.append("unstop")
    except Exception as e:
        check("Unstop scraper loads", False, str(e))

    try:
        from platforms.generic_web import GenericWebPlatform
        check("GenericWeb scraper loads", True)
        platforms_ok.append("generic_web")
    except Exception as e:
        check("GenericWeb scraper loads", False, str(e))

    # ═══════════════════════════════════════════════════════════
    # 9. AI MODULES
    # ═══════════════════════════════════════════════════════════
    print("\n--- 9. AI Modules ---")

    try:
        from agent.filter import filter_listings
        check("AI Filter (agent/filter.py)", True)
    except Exception as e:
        check("AI Filter (agent/filter.py)", False, str(e))

    try:
        from agent.cover_note import generate_cover_note
        check("AI Cover Note (agent/cover_note.py)", True)
    except Exception as e:
        check("AI Cover Note (agent/cover_note.py)", False, str(e))

    try:
        from agent.form_filler import answer_question
        check("AI Form Filler (agent/form_filler.py)", True)
    except Exception as e:
        check("AI Form Filler (agent/form_filler.py)", False, str(e))

    try:
        from agent.interview_prep import generate_interview_prep
        check("AI Interview Prep (agent/interview_prep.py)", True)
    except Exception as e:
        check("AI Interview Prep (agent/interview_prep.py)", False, str(e))

    # ═══════════════════════════════════════════════════════════
    # 10. LOG FILES & TRACKER
    # ═══════════════════════════════════════════════════════════
    print("\n--- 10. Logs & Tracker ---")

    log_dir = Path("./logs")
    check("logs/ directory exists", log_dir.exists(), "Missing logs directory")

    csv_path = Path("./logs/applications.csv")
    if csv_path.exists():
        with open(csv_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        total = max(0, len(lines) - 1)  # minus header
        applied = sum(1 for l in lines if ",Applied," in l)
        errors = sum(1 for l in lines if ",Error" in l)
        pending = sum(1 for l in lines if ",Pending" in l)
        check(f"applications.csv ({total} records)", True)
        print(f"{INFO} Applied: {applied} | Errors: {errors} | Pending: {pending}")
    else:
        check("applications.csv", False, "No application history found", warn=True)

    # ═══════════════════════════════════════════════════════════
    # 11. BOT BEHAVIOR SETTINGS
    # ═══════════════════════════════════════════════════════════
    print("\n--- 11. Bot Behavior Settings ---")

    max_apps = os.getenv("MAX_APPLICATIONS_PER_RUN", "10")
    dry_run = os.getenv("DRY_RUN", "false")
    print(f"{INFO} MAX_APPLICATIONS_PER_RUN: {max_apps}")
    print(f"{INFO} DRY_RUN: {dry_run}")
    check("DRY_RUN is off", dry_run.lower() == "false", "DRY_RUN=true — bot won't actually apply!", warn=True)

    caps = {
        "INTERNSHALA_MAX_APPLIES": os.getenv("INTERNSHALA_MAX_APPLIES", "15"),
        "LINKEDIN_MAX_APPLIES": os.getenv("LINKEDIN_MAX_APPLIES", "10"),
        "INDEED_MAX_APPLIES": os.getenv("INDEED_MAX_APPLIES", "10"),
        "UNSTOP_MAX_APPLIES": os.getenv("UNSTOP_MAX_APPLIES", "15"),
    }
    for k, v in caps.items():
        print(f"{INFO} {k}: {v}")

    # ═══════════════════════════════════════════════════════════
    # 12. LIVE SCRAPER TEST (lightweight)
    # ═══════════════════════════════════════════════════════════
    print("\n--- 12. Live Scraper Quick Test ---")

    if "internshala" in platforms_ok:
        try:
            p = InternshalaPlatform()
            results_list = p.search(profile)
            count = len(results_list)
            check(f"Internshala live scrape ({count} listings)", count > 0,
                  "0 results — site may be down or blocked")
        except Exception as e:
            check("Internshala live scrape", False, str(e))

    if "unstop" in platforms_ok:
        try:
            p = UnstopPlatform()
            results_list = p.search(profile)
            count = len(results_list)
            check(f"Unstop live scrape ({count} listings)", count > 0,
                  "0 results — site may be down or blocked")
        except Exception as e:
            check("Unstop live scrape", False, str(e))

    if "indeed" in platforms_ok:
        try:
            p = IndeedPlatform()
            results_list = p.search(profile)
            count = len(results_list)
            check(f"Indeed live scrape ({count} listings)", count > 0,
                  "0 results — site may be down or blocked", warn=True)
        except Exception as e:
            check("Indeed live scrape", False, str(e), warn=True)

    # ═══════════════════════════════════════════════════════════
    # SUMMARY
    # ═══════════════════════════════════════════════════════════
    print("\n" + "=" * 60)
    print("  PREFLIGHT CHECK COMPLETE")
    print("=" * 60)
    print(f"  PASS: {results['pass']}")
    print(f"  FAIL: {results['fail']}")
    print(f"  WARN: {results['warn']}")
    print("=" * 60)

    if results["fail"] == 0:
        print("\n  >>> ALL CRITICAL CHECKS PASSED! Bot is ready to run. <<<")
        print("  Run:  python main.py --run-now")
    else:
        print(f"\n  >>> {results['fail']} CRITICAL ISSUE(S) found. Fix them before running the bot. <<<")

    return results["fail"]


if __name__ == "__main__":
    sys.exit(main())
