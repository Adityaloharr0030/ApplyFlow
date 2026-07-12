"""
agent/filter.py
───────────────
Resume-aware listing scorer.

Two modes:
  1. AI mode  — Gemini with full resume context + outcome learning injected
  2. Local mode — keyword scoring (offline fallback)

The AI prompt now includes:
  - Your actual resume text (projects, tech stacks, achievements)
  - Patterns learned from 365+ past applications (what worked, what didn't)
  - Strict JSON-only output
"""

import json
import logging
import os
import re
import time

logger = logging.getLogger(__name__)

API_CALL_DELAY = 2.5
MAX_RETRIES = 2

from agent.ai_client import get_ai_response

_ai_disabled = False

# Lazy-loaded singletons — loaded once per run
_resume_ctx = None
_outcome_ctx = None


def _get_resume_ctx():
    global _resume_ctx
    if _resume_ctx is None:
        try:
            from agent.resume_brain import get_resume_context
            _resume_ctx = get_resume_context()
        except Exception as e:
            logger.debug(f"[Filter] Resume brain unavailable: {e}")
            _resume_ctx = None
    return _resume_ctx


def _get_outcome_ctx():
    global _outcome_ctx
    if _outcome_ctx is None:
        try:
            from agent.outcome_tracker import get_outcome_context
            _outcome_ctx = get_outcome_context()
        except Exception as e:
            logger.debug(f"[Filter] Outcome tracker unavailable: {e}")
            _outcome_ctx = None
    return _outcome_ctx


# ── Local keyword fallback ─────────────────────────────────────────────────────

def _score_with_keywords(listing: dict, profile: dict) -> dict:
    """Score a listing locally using keyword matching (no API needed)."""
    title       = listing.get("title", "").lower()
    company     = listing.get("company", "").lower()
    location    = listing.get("location", "").lower()
    description = listing.get("description", "").lower()

    score = 3
    reasons = []

    skills = [s.lower() for s in profile.get("skills", [])]
    skill_matches = [s for s in skills if s in title or s in description]
    if len(skill_matches) >= 3:
        score += 4
        reasons.append(f"Strong skill match: {', '.join(skill_matches[:3])}")
    elif len(skill_matches) >= 2:
        score += 3
        reasons.append(f"Good skill match: {', '.join(skill_matches[:2])}")
    elif skill_matches:
        score += 2
        reasons.append(f"Skill match: {skill_matches[0]}")

    keywords = [k.lower() for k in profile.get("keywords", [])]
    kw_matches = [k for k in keywords if k in title or k in description]
    if len(kw_matches) >= 2:
        score += 2
        reasons.append(f"Keywords: {', '.join(kw_matches[:2])}")
    elif kw_matches:
        score += 1
        reasons.append(f"Keyword: {kw_matches[0]}")

    for pref in [m.lower() for m in profile.get("location_preferences", [])]:
        if pref in location:
            score += 1
            reasons.append(f"Location: {pref}")
            break

    for excl in [c.lower() for c in profile.get("exclude_keywords", [])]:
        if excl in title:
            score = max(1, score - 3)
            reasons = [f"Excluded keyword: {excl}"]
            break

    # Outcome context boost
    oct_ctx = _get_outcome_ctx()
    if oct_ctx:
        good_kws = oct_ctx.good_title_keywords
        if any(kw in title for kw in good_kws):
            score += 1
            reasons.append("Matches past successful role keywords")
        if oct_ctx.is_bad_company(company):
            score = 1
            reasons = [f"Error-blocked company: {company}"]

    score = max(1, min(10, score))
    return {"score": score, "reason": "; ".join(reasons) or "General listing", "apply": score >= 4}


# ── AI scoring with resume + outcome context ───────────────────────────────────

def _score_with_ai(listing: dict, profile: dict) -> dict | None:
    global _ai_disabled
    if _ai_disabled:
        return None

    resume_ctx = _get_resume_ctx()
    outcome_ctx = _get_outcome_ctx()

    # Build the resume summary block
    if resume_ctx:
        resume_block = resume_ctx.summary_for_prompt(max_chars=1400)
    else:
        # Fallback to profile.json data
        resume_block = (
            f"Name: {profile.get('name')}\n"
            f"Degree: {profile.get('degree')}\n"
            f"College: {profile.get('college')}\n"
            f"Skills: {', '.join(profile.get('skills', []))}\n"
            f"Projects: {', '.join(profile.get('projects', []))}"
        )

    outcome_block = outcome_ctx.scoring_hint() if outcome_ctx else ""

    desc = listing.get("description", "")[:1000]

    system_prompt = "You are a precise internship matching assistant. Return ONLY valid JSON — no markdown, no explanation."
    user_prompt = f"""Score this internship listing for the following candidate based on their ACTUAL RESUME.

══ CANDIDATE RESUME ══
{resume_block}

══ PAST APPLICATION LEARNING ══
{outcome_block}

══ INTERNSHIP LISTING ══
Title: {listing.get('title', 'N/A')}
Company: {listing.get('company', 'N/A')}
Location: {listing.get('location', 'N/A')}
Duration: {listing.get('duration', 'N/A')}
Stipend: {listing.get('stipend', 'N/A')}
Description: {desc}

══ SCORING RULES ══
Score 9-10: Perfect match — title directly uses candidate's main tech stack (Flutter/React/Node/Java), remote or target city
Score 7-8 : Good match — 2+ skills overlap, domain aligns with candidate's projects
Score 6   : Acceptable — some overlap, worth applying
Score 4-5 : Weak — generic or unrelated role, but not explicitly excluded
Score 1-3 : Skip — excluded keyword in title (sales/HR/marketing/SEO), unpaid with relocation, or company in bad list

RESPOND ONLY WITH JSON:
{{"score": <integer 1-10>, "reason": "<one specific sentence mentioning the overlap>", "apply": <true if score >= 4>}}"""

    try:
        text = get_ai_response(system_prompt, user_prompt, max_tokens=200, response_format="json", model_type="scorer")
        if not text:
            return None

        text = text.strip().replace("```json", "").replace("```", "").strip()
        result = json.loads(text)
        score = max(1, min(10, int(result.get("score", 0))))
        return {
            "score": score,
            "reason": str(result.get("reason", "AI scored")),
            "apply": score >= 4,
        }

    except json.JSONDecodeError:
        m = re.search(r'"score"\s*:\s*(\d+)', text or "")
        if m:
            score = max(1, min(10, int(m.group(1))))
            return {"score": score, "reason": "AI scored (regex fallback)", "apply": score >= 4}
        return None

    except Exception as e:
        logger.warning(f"[Filter] AI models exhausted or failed: {e}. Switching to keyword scoring for remaining.")
        _ai_disabled = True
        return None


# ── Public API ────────────────────────────────────────────────────────────────

def score_listing(listing: dict, profile: dict) -> dict:
    default = {"score": 0, "reason": "Could not score", "apply": False}
    try:
        if not _ai_disabled:
            ai_result = _score_with_ai(listing, profile)
            if ai_result:
                status = "YES" if ai_result["apply"] else "SKIP"
                logger.info(
                    f"  [{status}] {listing.get('title', '?')} @ {listing.get('company', '?')} "
                    f"→ {ai_result['score']}/10 (AI+resume) — {ai_result['reason']}"
                )
                return ai_result

        local = _score_with_keywords(listing, profile)
        status = "YES" if local["apply"] else "SKIP"
        logger.info(
            f"  [{status}] {listing.get('title', '?')} @ {listing.get('company', '?')} "
            f"→ {local['score']}/10 (local) — {local['reason']}"
        )
        return local

    except Exception as e:
        logger.warning(f"  [X] Error scoring: {e}")
        return default


def filter_listings(listings: list[dict], profile: dict) -> list[dict]:
    """Score all listings, skip duplicates and bad companies, return approved list."""
    global _ai_disabled, _resume_ctx, _outcome_ctx
    _ai_disabled = False
    _resume_ctx = None   # reset per run so context is reloaded fresh
    _outcome_ctx = None

    # Pre-load contexts and log status
    resume_ctx = _get_resume_ctx()
    outcome_ctx = _get_outcome_ctx()

    if resume_ctx:
        logger.info(f"[Filter] 🧠 Resume-aware scoring — {resume_ctx.name}, {len(resume_ctx.skills)} skills, {len(resume_ctx.projects)} projects")
    else:
        logger.warning("[Filter] Resume brain unavailable — using profile.json skills only")

    if outcome_ctx:
        logger.info(f"[Filter] 📊 Outcome context — {outcome_ctx.applied_count} past successes, {len(outcome_ctx.bad_companies)} bad companies, {len(outcome_ctx.already_applied)} duplicates to skip")

    avoid_companies = {c.lower() for c in profile.get("avoid_companies", [])}
    exclude_kws = [k.lower() for k in profile.get("exclude_keywords", [])]

    approved: list[dict] = []

    logger.info(f"[Filter] Scoring {len(listings)} listing(s)...")
    for i, listing in enumerate(listings, 1):
        company = listing.get("company", "").lower().strip()
        title   = listing.get("title", "").lower().strip()
        role    = listing.get("role", title)

        # Hard skip: blacklisted company
        if company in avoid_companies:
            logger.info(f"  [BLOCKED] {listing.get('company')} — avoid_companies list")
            continue

        # Hard skip: bad company from outcome tracker
        if outcome_ctx and outcome_ctx.is_bad_company(company):
            logger.info(f"  [BLOCKED] {listing.get('company')} — always errors (from history)")
            continue

        # Hard skip: excluded title keyword
        if any(kw in title for kw in exclude_kws):
            logger.info(f"  [SKIP] '{listing.get('title')}' — excluded keyword")
            continue

        # Soft skip: already applied this week
        if outcome_ctx and outcome_ctx.is_duplicate(company, role):
            logger.info(f"  [DUP] {listing.get('company')} / {listing.get('title')} — already applied")
            continue

        if i % 25 == 0:
            logger.info(f"  --- Progress: {i}/{len(listings)} ---")

        result = score_listing(listing, profile)

        if result["apply"]:
            listing["score"] = result["score"]
            listing["reason"] = result["reason"]
            approved.append(listing)

        if not _ai_disabled:
            time.sleep(API_CALL_DELAY)

    mode = "AI+Resume" if not _ai_disabled else "Local keyword"
    logger.info(f"[Filter] Done ({mode}): {len(approved)}/{len(listings)} approved")
    return approved
