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

from agent.ai_client import get_ai_response

# Track if AI failed so we stop retrying for the rest of the run
_ai_disabled = False


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


def _fetch_job_description(listing: dict) -> str:
    """Fetch the full job description if not present."""
    desc = listing.get('description', '')
    # If description is too short, we could scrape the apply_url here. 
    # For now, we rely on the snippet already scraped by the platform.
    return desc


def _score_with_ai(listing: dict, profile: dict) -> dict | None:
    """
    Score using unified AI client. Returns None if the API call fails.
    """
    global _ai_disabled
    if _ai_disabled:
        return None

    desc = _fetch_job_description(listing)
    
    system_prompt = "You are a career advisor. Return ONLY JSON."
    user_prompt = f"""Score this internship/job match 1-10.

LISTING: {listing.get('title', 'N/A')} at {listing.get('company', 'N/A')} ({listing.get('location', 'N/A')})
DESCRIPTION: {desc[:1500]}
CANDIDATE SKILLS: {', '.join(profile.get('skills', []))}
CANDIDATE KEYWORDS: {', '.join(profile.get('keywords', []))}
LOCATION PREFERENCES: {', '.join(profile.get('location_preferences', []))}

Respond ONLY with JSON: {{"score": <1-10>, "reason": "<short reason>", "apply": <true/false>}}"""

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            text = get_ai_response(system_prompt, user_prompt, max_tokens=1024, response_format="json")
            if not text:
                return None

            text = text.strip()
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
            if "429" in err_str or "quota" in err_str or "rate" in err_str or "resource_exhausted" in err_str:
                if attempt < MAX_RETRIES:
                    wait = 8 * (2 ** attempt)
                    logger.info(f"  [Retry {attempt}/{MAX_RETRIES}] Rate limited, waiting {wait}s...")
                    time.sleep(wait)
                else:
                    logger.warning("[Filter] AI quota exhausted -- switching to local keyword scoring")
                    _ai_disabled = True
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
        if not _ai_disabled:
            ai_result = _score_with_ai(listing, profile)
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
    global _ai_disabled
    _ai_disabled = False  # Reset per pipeline run (fixes silent degradation across scheduler runs)

    mode = "local keyword matching (AI disabled)" if _ai_disabled else "AI scoring"
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

        # Delay between API calls (only if using AI)
        if not _ai_disabled:
            time.sleep(API_CALL_DELAY)

    logger.info(
        f"[Filter] Done: {len(approved)}/{len(listings)} listings approved for application"
    )
    return approved
