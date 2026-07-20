"""
agent/interview_prep.py
───────────────────────
Generates personalized interview prep questions and answers
after a successful job application.
"""

import logging
import os
from pathlib import Path
from datetime import datetime
from agent.ai_client import get_ai_response

logger = logging.getLogger(__name__)

def generate_interview_prep(listing: dict, profile: dict, save_dir: str = "logs/prep"):
    """
    Generates an interview prep guide based on the listing and profile.
    Saves it to a text file in the specified directory.
    """
    company = listing.get("company", "Unknown Company")
    title = listing.get("title", "Unknown Role")
    desc = listing.get("description", "")
    
    # Don't waste AI tokens if we have basically no info
    if not company or company == "Unknown Company":
        return

    logger.info(f"[InterviewPrep] Generating prep guide for {title} @ {company}...")

    system_prompt = "You are an expert technical recruiter and interview coach."
    user_prompt = f"""Generate a short, targeted interview preparation guide for this specific role.

ROLE: {title} at {company}
JOB DESCRIPTION: {desc[:1500]}

CANDIDATE SKILLS: {', '.join(profile.get('skills', []))}
CANDIDATE EXPERIENCE: {profile.get('projects', [])}

Please provide:
1. **Top 3 likely interview questions** based on the job description.
2. **Suggested speaking points** for the candidate to answer each question, leveraging their specific skills/projects.
3. **1 key thing to research** about {company} before the interview.

Format the output clearly using Markdown. Be extremely concise and actionable.
"""

    try:
        prep_content = get_ai_response(system_prompt, user_prompt, max_tokens=1500, response_format="text", user_id=profile.user_id if profile else None)
        
        if not prep_content:
            logger.warning("[InterviewPrep] AI failed to generate prep content.")
            return

        # Ensure directory exists
        out_dir = Path(save_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        
        # Save to file
        safe_company = "".join(c if c.isalnum() else "_" for c in company).strip("_")
        date_str = datetime.now().strftime("%Y%m%d")
        filename = f"{date_str}_{safe_company}_prep.md"
        filepath = out_dir / filename
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"# Interview Prep: {title} @ {company}\n\n")
            f.write(prep_content.strip())
            
        logger.info(f"  [InterviewPrep] Saved guide to {filepath}")
        
    except Exception as e:
        logger.error(f"[InterviewPrep] Error generating guide: {e}")
