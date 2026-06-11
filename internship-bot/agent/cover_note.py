"""
agent/cover_note.py
───────────────────
Generates a personalized cover note for a given internship listing.
- Tries Google Gemini API (free tier) first
- Falls back to a local template if the API key is missing or quota is exhausted
"""

import logging
import os
import time

logger = logging.getLogger(__name__)

# Fallback template
LOCAL_TEMPLATE = """Dear Hiring Manager,

I am writing to express my interest in the {title} internship at {company}. As a student pursuing a {degree} (Class of {year}), I am eager to apply my academic knowledge in a practical setting.

My skills include: {skills}

I am passionate about building efficient and user-friendly software solutions, and I am confident that I can make a meaningful contribution to your team. I am particularly drawn to this opportunity because it aligns perfectly with my career goals and areas of interest ({keywords}).

Thank you for considering my application. I have attached my resume for your review and look forward to the possibility of discussing this opportunity with you.

Best regards,
{name}"""


def _get_model():
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key or api_key == "your_gemini_key_here":
        return None

    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        return genai.GenerativeModel("gemini-2.0-flash")
    except Exception as e:
        logger.warning(f"[CoverNote] Could not initialize Gemini: {e}")
        return None


def generate_cover_note(listing: dict, profile: dict) -> str:
    """
    Generate a cover note. Tries Gemini AI first, falls back to a local template.
    """
    title = listing.get("title", "Software Engineering")
    company = listing.get("company", "your company")

    model = _get_model()
    if model:
        prompt = f"""Write a short, professional cover letter for the following internship.

INTERNSHIP: {title} at {company}

CANDIDATE PROFILE:
Name: {profile.get('name', '[Name]')}
Degree: {profile.get('degree', '[Degree]')} ({profile.get('year', '[Year]')})
Skills: {', '.join(profile.get('skills', []))}

RULES:
1. Keep it under 150 words.
2. Be professional and concise.
3. Do not include placeholder brackets like [Address] or [Date].
4. Output ONLY the letter text. No markdown formatting.
"""
        for attempt in range(1, 3):
            try:
                response = model.generate_content(prompt)
                text = response.text.strip()
                if text:
                    return text
            except Exception as e:
                err_str = str(e).lower()
                if "429" in err_str or "quota" in err_str or "rate" in err_str:
                    logger.debug("[CoverNote] Quota exhausted -- falling back to local template")
                    break  # Stop retrying on quota errors
                else:
                    logger.warning(f"[CoverNote] Gemini error: {e}")
                    time.sleep(2)

    # --- Local Fallback ---
    logger.info("  [CoverNote] Using local offline template")
    skills = ", ".join(profile.get("skills", ["software development"]))
    keywords = ", ".join(profile.get("keywords", ["technology"]))
    
    return LOCAL_TEMPLATE.format(
        title=title,
        company=company,
        name=profile.get("name", "[Your Name]"),
        degree=profile.get("degree", "[Your Degree]"),
        year=profile.get("year", "[Year]"),
        skills=skills,
        keywords=keywords
    )
