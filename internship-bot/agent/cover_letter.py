from agent.ai_client import get_ai_response
from core.models import UserProfile, JobListing
import logging

logger = logging.getLogger(__name__)

def generate_cover_letter(profile: UserProfile, listing: JobListing) -> str:
    """Generate a tailored cover letter using AI based on the user's profile and the job listing."""
    system_prompt = "You are a professional career coach. Write a brief, punchy, and highly tailored cover letter or 'About Me' blurb for an internship application. Do not include placeholder names or signature blocks at the end, just the body of the letter. Keep it under 250 words."
    
    user_prompt = f"""
Candidate Profile:
Name: {profile.name}
Degree: {profile.degree}
College: {profile.college}
Skills: {', '.join(profile.skills)}
Projects: {', '.join(profile.projects)}
Achievements: {profile.achievement}

Job Listing:
Title: {listing.title}
Company: {listing.company}
Description: {listing.description[:1500]}

Please write the cover letter for this candidate applying to this specific role. Focus on matching the candidate's skills to the job description.
    """
    
    try:
        response = get_ai_response(system_prompt, user_prompt, max_tokens=300, model_type="writer", user_id=profile.user_id if profile else None)
        if not response:
            return "I am very interested in this role and believe my skills make me a strong candidate. Please find my resume attached."
        return response.strip()
    except Exception as e:
        logger.error(f"Failed to generate cover letter: {e}")
        return "I am very interested in this role and believe my skills make me a strong candidate. Please find my resume attached."
