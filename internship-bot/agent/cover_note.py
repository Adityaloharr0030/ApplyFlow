"""
agent/cover_note.py
───────────────────
Generates a personalized cover note for a given internship listing.
- Tries Google Gemini API (free tier) first
- Injects ACTUAL RESUME context (from agent/resume_brain.py)
- Falls back to a rich local template if the API key is missing or quota is exhausted
"""

import logging
import time

logger = logging.getLogger(__name__)

from agent.ai_client import get_ai_response

# Lazy-loaded singleton
_resume_ctx = None

def _get_resume_ctx():
    global _resume_ctx
    if _resume_ctx is None:
        try:
            from agent.resume_brain import get_resume_context
            _resume_ctx = get_resume_context()
        except Exception as e:
            logger.debug(f"[CoverNote] Resume brain unavailable: {e}")
            _resume_ctx = None
    return _resume_ctx


def generate_cover_note(listing: dict, profile: dict) -> str:
    """
    Generate a personalized cover note using actual resume context.
    Tries Gemini AI first, falls back to a rich local template.
    """
    title = listing.get("title", "Software Engineering Internship")
    company = listing.get("company", "your company")
    location = listing.get("location", "")

    resume_ctx = _get_resume_ctx()

    if resume_ctx:
        resume_block = resume_ctx.cover_note_block(title)
        name = resume_ctx.name or profile.get("name", "Candidate")
        email = resume_ctx.email or profile.get("email", "")
    else:
        name = profile.get("name", "Aditya Lohar")
        degree = profile.get("degree", "B.Tech Computer Engineering")
        year = profile.get("year", "2027")
        college = profile.get("college", "KBSCOE, Jalgaon (DBATU)")
        email = profile.get("email", "")
        github = profile.get("github", "github.com/Adityaloharaa0030")
        skills_list = profile.get("skills", ["Flutter", "React", "Node.js"])
        projects = profile.get("projects", [
            "CrazyXAni (anime streaming platform with Next.js + Node.js + MongoDB)",
            "Krushi Mitra (AI-powered farming app)"
        ])
        achievement = profile.get("achievement", "Top ~800 of 31,000+ at Meta PyTorch OpenEnv Hackathon")

        resume_block = (
            f"Name: {name}\n"
            f"Degree: {degree}, graduating {year}\n"
            f"College: {college}\n"
            f"Skills: {', '.join(skills_list)}\n"
            f"Projects: {chr(10).join(f'  - {p}' for p in projects[:3])}\n"
            f"GitHub: {github}\n"
            f"Achievement: {achievement}"
        )

    system_prompt = "You are a professional cover letter writer. Output plain text only. Do NOT use markdown."
    user_prompt = f"""Write a SHORT, SPECIFIC cover letter for this internship application.

INTERNSHIP DETAILS:
- Role: {title}
- Company: {company}
- Location: {location}
- Stipend: {listing.get('stipend', 'not listed')}

CANDIDATE ACTUAL BACKGROUND:
{resume_block}

STRICT RULES:
1. Maximum 120 words — recruiters skip long letters.
2. Mention the COMPANY NAME and ROLE specifically (not generic).
3. Reference EXACTLY ONE specific project from the candidate background that best matches this role.
4. Mention the candidate's core tech stack that matches the role.
5. End with the candidate's name: {name}
6. NO placeholder brackets like [Your Name] or [Date].
7. NO markdown — plain text only.
8. Professional but direct — not sycophantic.

OUTPUT: Plain text letter only. Nothing else."""

    try:
        text = get_ai_response(system_prompt, user_prompt, max_tokens=400, response_format="text", model_type="cover", user_id=profile.user_id if profile else None)
        if text and len(text.strip()) > 60:
            # Basic cleanup
            text = text.replace("Dear Hiring Manager", "Dear Hiring Team")
            return text.strip()
    except Exception as e:
        logger.warning(f"[CoverNote] AI models failed or exhausted quotas: {e}. Falling back to local template.")

    # ── Rich Local Fallback using parsed resume data ──
    logger.info("  [CoverNote] Using local offline template")

    if resume_ctx:
        # Resume context IS available — derive everything from it
        proj = resume_ctx.best_project_for(title)
        proj_name = proj.get("name", resume_ctx.project_names()[0] if resume_ctx.project_names() else "my recent project")
        techs = ", ".join(proj.get("techs", [])[:3])
        skills_top3 = resume_ctx.top_skills(3)
        degree_line = f"{resume_ctx.degree} at {resume_ctx.college} (graduating {resume_ctx.graduation_year})"
        achiev = resume_ctx.achievements[0] if resume_ctx.achievements else ""
    else:
        # Resume context NOT available — use profile.json locals (guaranteed defined in this branch)
        proj_name = projects[0] if projects else "my recent project"
        techs = skills_list[0] if skills_list else "software engineering"
        skills_top3 = ", ".join(skills_list[:3])
        degree_line = f"{degree} at {college} (graduating {year})"
        achiev = achievement

    achiev_sentence = f" I also achieved {achiev}." if achiev else ""

    return f"""Dear Hiring Team,

I am {name}, a {degree_line}, applying for the {title} position at {company}.

My core technical skills include {skills_top3}. I recently built {proj_name} using {techs}, which gave me hands-on experience with production-level architecture and complex APIs.{achiev_sentence}

I am available to start immediately and excited to contribute my skills to your engineering team.

Regards,
{name}
{email}"""

