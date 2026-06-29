import logging
import os
import json

logger = logging.getLogger(__name__)

from agent.ai_client import get_ai_response

def answer_question(question: str, profile: dict) -> str:
    """
    Generate a smart, contextual answer to an application form question using Gemini.
    """
    try:
        system_prompt = "You are answering a specific question on a job application form on behalf of the candidate."
        user_prompt = f"""Keep the answer extremely concise, professional, and directly address the question (1-3 sentences max). Do not write a full cover letter.

CANDIDATE INFO:
Name: {profile.get('name', '')}
Degree: {profile.get('degree', '')} ({profile.get('year', '')})
Skills: {', '.join(profile.get('skills', []))}
Experience/Projects: {json.dumps(profile.get('projects', []))}

QUESTION: "{question}"

Write ONLY the answer to the question."""

        answer = get_ai_response(system_prompt, user_prompt, max_tokens=512, response_format="text")
        
        if not answer:
            return "Yes, I am available to start immediately and meet the requirements."
        logger.info(f"  [FormFiller] Generated AI answer for question: {question[:30]}...")
        return answer.strip()
    except Exception as e:
        logger.error(f"  [FormFiller] Failed to generate answer: {e}")
        return "Yes, I am available to start immediately and meet the requirements."

