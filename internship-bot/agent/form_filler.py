import logging
import os
import json

logger = logging.getLogger(__name__)

def _get_client():
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key or api_key == "your_gemini_key_here":
        return None
    try:
        from google import genai as google_genai
        return google_genai.Client(api_key=api_key)
    except Exception as e:
        logger.warning(f"[FormFiller] Could not initialize Gemini client: {e}")
        return None

def answer_question(question: str, profile: dict) -> str:
    """
    Generate a smart, contextual answer to an application form question using Gemini.
    """
    client = _get_client()
    if not client:
        return "Yes, I am available to start immediately and meet the requirements."

    try:
        MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
        prompt = f"""You are answering a specific question on a job application form on behalf of the candidate.
Keep the answer extremely concise, professional, and directly address the question (1-3 sentences max). Do not write a full cover letter.

CANDIDATE INFO:
Name: {profile.get('name', '')}
Degree: {profile.get('degree', '')} ({profile.get('year', '')})
Skills: {', '.join(profile.get('skills', []))}
Experience/Projects: {json.dumps(profile.get('projects', []))}

QUESTION: "{question}"

Write ONLY the answer to the question."""

        from google.genai import types as genai_types
        response = client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=genai_types.GenerateContentConfig(max_output_tokens=150)
        )
        answer = response.text.strip()
        logger.info(f"  [FormFiller] Generated AI answer for question: {question[:30]}...")
        return answer
    except Exception as e:
        logger.error(f"  [FormFiller] Failed to generate answer: {e}")
        return "Yes, I am available to start immediately and meet the requirements."
