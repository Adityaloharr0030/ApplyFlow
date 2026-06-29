"""
agent/ai_client.py
──────────────────
Unified AI Client for ApplyFlow.
Provides a single interface for AI calls.
Prioritizes Anthropic (Claude) if an API key is available.
Falls back to Google Gemini if Anthropic is not configured.
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Constants
CLAUDE_MODEL = "claude-3-5-sonnet-20241022"
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


def get_ai_response(system_prompt: str, user_prompt: str, max_tokens: int = 1024, response_format: str = "text") -> Optional[str]:
    """
    Get a response from the available AI provider.
    Tries Anthropic first, falls back to Gemini.
    
    Args:
        system_prompt: The system instruction for the AI.
        user_prompt: The user input.
        max_tokens: Maximum tokens to generate.
        response_format: 'text' or 'json' (helps guide the model if supported).
        
    Returns:
        The generated text, or None if no AI is available or an error occurred.
    """
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    
    if anthropic_key and anthropic_key != "your_key_here":
        return _call_anthropic(anthropic_key, system_prompt, user_prompt, max_tokens)
    elif gemini_key and gemini_key != "your_api_key_here":
        return _call_gemini(gemini_key, system_prompt, user_prompt, max_tokens, response_format)
    else:
        logger.warning("[AI] No valid API keys found (Anthropic or Gemini).")
        return None


def _call_anthropic(api_key: str, system_prompt: str, user_prompt: str, max_tokens: int) -> Optional[str]:
    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)
        
        logger.debug(f"[AI] Calling Anthropic ({CLAUDE_MODEL})")
        message = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )
        return message.content[0].text
    except ImportError:
        logger.warning("[AI] 'anthropic' library not installed. Falling back to Gemini.")
        gemini_key = os.getenv("GEMINI_API_KEY", "")
        if gemini_key and gemini_key != "your_api_key_here":
             return _call_gemini(gemini_key, system_prompt, user_prompt, max_tokens, "text")
        return None
    except Exception as e:
        logger.error(f"[AI] Anthropic API Error: {e}")
        return None


def _call_gemini(api_key: str, system_prompt: str, user_prompt: str, max_tokens: int, response_format: str) -> Optional[str]:
    try:
        from google import genai
        from google.genai import types
        
        client = genai.Client(api_key=api_key)
        
        config_kwargs = {
            "system_instruction": system_prompt,
            "temperature": 0.7,
            "max_output_tokens": max_tokens,
        }
        
        if response_format == "json":
             config_kwargs["response_mime_type"] = "application/json"
             
        config = types.GenerateContentConfig(**config_kwargs)
        
        logger.debug(f"[AI] Calling Gemini ({GEMINI_MODEL})")
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=user_prompt,
            config=config
        )
        return response.text
    except Exception as e:
        logger.error(f"[AI] Gemini API Error: {e}")
        return None
