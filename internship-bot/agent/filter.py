"""
agent/filter.py
───────────────
Listing scorer with two modes:
  1. AI mode  — Uses Google Gemini (free tier) if GEMINI_API_KEY is valid
  2. Local mode — Keyword-based scoring (no API needed, works offline)

Falls back to local mode automatically if the API key is missing or quota is exhausted.
"""

import json
import logging
import os
import time

logger = logging.getLogger(__name__)

# Rate limiting for API calls
API_CALL_DELAY = 4.0
MAX_RETRIES = 2

# Track if Gemini failed so we stop retrying for the rest of the run
_gemini_disabled = False


def _get_client():
    """
    Configure and return a Gemini client instance.
    Returns None if the API key is missing or Gemini was disabled this run.
    """
    global _gemini_disabled
    if _gemini_disabled:
        return None

    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key or api_key == "your_gemini_key_here":
        return None

    try:
        from google import genai as google_genai
        client = google_genai.Client(api_key=api_key)
        return client
    except Exception as e:
        logger.warning(f"[Filter] Could not initialize Gemini client: {e}")
        return None


def _score_with_keywords(listing: dict, profile: dict) -> dict:
    """
    Score a listing locally using keyword matching (no API needed).
    Checks title, company, location, AND description for matches.
    """
    title = listing.get("title", "").lower()
    company = listing.get("company", "").lower()
    location = listing.get("location", "").lower()
    description = listing.get("description", "").lower()
    # Combine all searchable text
    full_text = f"{title} {company} {description}"

    score = 3  # Base score
    reasons = []

    # --- Skill matching (strongest signal) — check title + description ---
    skills = [s.lower() for s in profile.get("skills", [])]
    skill_matches = [s for s in skills if s in title or s in description]
    if len(skill_matches) >= 3:
        score += 4
        reasons.append(f"Strong skill match: {', '.join(skill_matches[:3])}")
    elif len(skill_matches) >= 2:
        score += 3
        reasons.append(f"Good skill match: {', '.join(skill_matches[:2])}")
    elif len(skill_matches) >= 1:
        score += 2
        reasons.append(f"Skill match: {skill_matches[0]}")

    # --- Keyword matching — check title + description ---
    keywords = [k.lower() for k in profile.get("keywords", [])]
    keyword_matches = [k for k in keywords if k in title or k in description]
    if len(keyword_matches) >= 2:
        score += 2
        reasons.append(f"Keywords: {', '.join(keyword_matches[:2])}")
    elif keyword_matches:
        score += 1
        reasons.append(f"Keyword: {keyword_matches[0]}")

    # --- Location / Remote preference ---
    location_prefs = [m.lower() for m in profile.get("location_preferences", [])]
    for pref in location_prefs:
        if pref in location:
            score += 1
            reasons.append(f"Location: {pref}")
            break

    # --- Exclude keywords (negative signals) ---
    exclude = [c.lower() for c in profile.get("exclude_keywords", [])]
    for excl in exclude:
        if excl in title:
            score = max(1, score - 3)
            reasons = [f"Excluded keyword in title: {excl}"]
            break

    # --- Negative signals ---
    avoid = [c.lower() for c in profile.get("avoid_companies", [])]
    if company in avoid:
        score = 1
        reasons = ["Blacklisted company"]

    # Clamp score
    score = max(1, min(10, score))
    reason = "; ".join(reasons) if reasons else "General listing"
    apply_decision = score >= 4  # Lowered to 4 to be more lenient when AI is unavailable

    return {"score": score, "reason": reason, "apply": apply_decision}


def _score_with_ai(listing: dict, profile: dict, client) -> dict | None:
    """
    Score using Gemini AI. Returns None if the API call fails (triggers fallback).
    """
    global _gemini_disabled

    MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
    prompt = f"""You are a career advisor. Score this internship/job match 1-10.

LISTING: {listing.get('title', 'N/A')} at {listing.get('company', 'N/A')} ({listing.get('location', 'N/A')})
CANDIDATE SKILLS: {', '.join(profile.get('skills', []))}
CANDIDATE KEYWORDS: {', '.join(profile.get('keywords', []))}
LOCATION PREFERENCES: {', '.join(profile.get('location_preferences', []))}

Respond ONLY with JSON: {{"score": <1-10>, "reason": "<short reason>", "apply": <true/false>}}"""

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            from google.genai import types as genai_types
            response = client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=genai_types.GenerateContentConfig(max_output_tokens=200)
            )
            text = response.text.strip()

            # Strip markdown fences
            if text.startswith("```"):
                lines = text.split("\n")
                text = "\n".join(l for l in lines if not l.startswith("```")).strip()

            result = json.loads(text)
            score = max(1, min(10, int(result.get("score", 0))))
            return {
                "score": score,
                "reason": str(result.get("reason", "AI scored")),
                "apply": score >= 5,
            }

        except Exception as e:
            err_str = str(e).lower()
            if "429" in str(e) or "quota" in err_str or "rate" in err_str or "resource_exhausted" in err_str:
                if attempt < MAX_RETRIES:
                    wait = 8 * (2 ** attempt)
                    logger.info(f"  [Retry {attempt}/{MAX_RETRIES}] Rate limited, waiting {wait}s...")
                    time.sleep(wait)
                else:
                    logger.warning(
                        "[Filter] Gemini quota exhausted -- switching to local keyword scoring"
                    )
                    _gemini_disabled = True
                    return None
            else:
                logger.debug(f"  AI scoring error: {e}")
                return None

    return None


def score_listing(listing: dict, profile: dict) -> dict:
    """
    Score a listing using AI (if available) or local keyword matching (fallback).
    """
    default_result = {"score": 0, "reason": "Could not score", "apply": False}

    try:
        # Try AI scoring first
        client = _get_client()
        if client:
            ai_result = _score_with_ai(listing, profile, client)
            if ai_result:
                status = "YES" if ai_result["apply"] else "SKIP"
                logger.info(
                    f"  [{status}] {listing.get('title', '?')} @ {listing.get('company', '?')} "
                    f"-> {ai_result['score']}/10 (AI) -- {ai_result['reason']}"
                )
                return ai_result

        # Fallback: local keyword scoring
        local_result = _score_with_keywords(listing, profile)
        status = "YES" if local_result["apply"] else "SKIP"
        logger.info(
            f"  [{status}] {listing.get('title', '?')} @ {listing.get('company', '?')} "
            f"-> {local_result['score']}/10 (local) -- {local_result['reason']}"
        )
        return local_result

    except Exception as e:
        logger.warning(f"  [X] Error scoring: {e}")
        return default_result


def filter_listings(listings: list[dict], profile: dict) -> list[dict]:
    """
    Score all listings and return only those worth applying to (score >= 5).
    Uses AI if available, otherwise falls back to local keyword matching.
    """
    client = _get_client()
    mode = "Gemini AI" if client else "local keyword matching (no API)"
    logger.info(f"[Filter] Scoring {len(listings)} listing(s) with {mode}...")

    approved: list[dict] = []
    avoid = {c.lower() for c in profile.get("avoid_companies", [])}

    for i, listing in enumerate(listings, 1):
        company = listing.get("company", "").lower()
        if company in avoid:
            logger.info(f"  [BLOCKED] {listing.get('company')}")
            continue

        if i % 25 == 0:
            logger.info(f"  --- Progress: {i}/{len(listings)} ---")

        result = score_listing(listing, profile)

        if result["apply"]:
            listing["score"] = result["score"]
            listing["reason"] = result["reason"]
            approved.append(listing)

        # Delay between API calls (only if using Gemini)
        if not _gemini_disabled and client:
            time.sleep(API_CALL_DELAY)

    logger.info(
        f"[Filter] Done: {len(approved)}/{len(listings)} listings approved for application"
    )
    return approved
