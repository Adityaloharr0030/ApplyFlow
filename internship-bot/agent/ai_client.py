"""
agent/ai_client.py
──────────────────
Unified AI Client for ApplyFlow.
Provides a robust multi-model fallback chain with smart routing:

Priority Order (fastest first):
1. Groq (Llama 3.3 70B) — blazing fast, used for cover notes & Q&A
2. Gemini (loops through all comma-separated keys)
3. Anthropic (Claude) — premium fallback

Smart Routing:
- "fast" tasks (cover notes, form Q&A) → Groq first, then Gemini
- "scorer" tasks (listing filtering) → Gemini first (better at structured output)
- "base" tasks → Groq first, then Gemini
"""

import os
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)

CLAUDE_MODEL = "claude-3-5-sonnet-20241022"

def _get_gemini_model(model_type: str) -> str:
    if model_type == "scorer":
        return os.getenv("TUNED_SCORER_MODEL", os.getenv("GEMINI_MODEL", "gemini-1.5-flash"))
    elif model_type == "cover":
        return os.getenv("TUNED_COVER_MODEL", os.getenv("GEMINI_MODEL", "gemini-1.5-flash"))
    return os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

class AILimitReached(Exception):
    """Raised when an API rate limit or quota is hit."""
    pass

# Global state to track exhausted keys during a run
_exhausted_keys = set()
_key_cycle = None
_last_keys_list = []

def reset_exhausted_keys():
    """Call this at the start of each bot run to clear exhausted key state."""
    global _exhausted_keys, _key_cycle, _last_keys_list
    _exhausted_keys = set()
    _key_cycle = None
    _last_keys_list = []
    logger.info("[AI] Reset all API key states for new run")

def _get_working_keys(model_type: str = "base") -> list[dict]:
    """
    Returns a list of dictionaries with 'provider' and 'api_key'.
    Excludes any keys that have been marked as exhausted (429) during this run.
    
    Smart routing:
    - For "scorer" tasks: Gemini first (better structured output), then Groq
    - For everything else: Groq first (fastest), then Gemini
    """
    groq_keys = []
    gemini_keys = []
    anthropic_keys = []
    
    # 1. Groq
    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    if groq_key and groq_key not in ("your_key_here", "") and groq_key not in _exhausted_keys:
        groq_keys.append({"provider": "groq", "api_key": groq_key})

    # 2. Gemini (can have multiple keys separated by comma)
    gemini_keys_str = os.getenv("GEMINI_API_KEY", "")
    for k in gemini_keys_str.split(","):
        k = k.strip()
        if k and k not in ("your_api_key_here", "your_gemini_key_here", "your_second_gemini_key_here") and k not in _exhausted_keys:
            gemini_keys.append({"provider": "gemini", "api_key": k})

    # 3. Anthropic
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if anthropic_key and anthropic_key not in ("your_key_here", "") and anthropic_key not in _exhausted_keys:
        anthropic_keys.append({"provider": "anthropic", "api_key": anthropic_key})

    # Smart routing based on task type
    if model_type == "scorer":
        # Scoring needs structured output → Gemini is better at this
        return gemini_keys + groq_keys + anthropic_keys
    else:
        # Cover notes, Q&A, base tasks → Groq is fastest
        return groq_keys + gemini_keys + anthropic_keys


def get_ai_response(system_prompt: str, user_prompt: str, max_tokens: int = 1024, response_format: str = "text", model_type: str = "base") -> Optional[str]:
    """
    Get a response from the AI.
    Uses round-robin load balancing across all working keys.
    If a 429/Rate Limit occurs, it bans that key for the rest of the run and fails over.
    """
    global _key_cycle, _last_keys_list
    
    working_keys = _get_working_keys(model_type)
    
    if not working_keys:
        logger.warning("[AI] No valid API keys found (all exhausted or none provided).")
        return None

    # Update cycle if working keys changed (e.g. one got banned)
    if working_keys != _last_keys_list:
        import itertools
        _last_keys_list = working_keys
        _key_cycle = itertools.cycle(working_keys)

    # We will try up to how many working keys we have
    attempts = len(working_keys)
    last_error = None
    
    for attempt in range(attempts):
        key_data = next(_key_cycle)
        provider = key_data["provider"]
        api_key = key_data["api_key"]
        
        try:
            if provider == "anthropic":
                return _call_anthropic(api_key, system_prompt, user_prompt, max_tokens)
            elif provider == "groq":
                masked = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "***"
                return _call_groq(api_key, system_prompt, user_prompt, max_tokens, masked, model_type)
            elif provider == "gemini":
                masked = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "***"
                return _call_gemini(api_key, system_prompt, user_prompt, max_tokens, response_format, masked, model_type)
                
        except AILimitReached as e:
            logger.warning(f"  [AI] {provider.capitalize()} hit limit: {e}. Removing key from rotation.")
            _exhausted_keys.add(api_key)
            last_error = e

            # Rebuild working keys immediately and reset the attempt budget
            working_keys = _get_working_keys(model_type)
            if not working_keys:
                logger.error("  [AI] ✗ All AI models/keys exhausted limits.")
                raise Exception("All AI quotas exhausted.") from e

            import itertools
            _last_keys_list = working_keys
            _key_cycle = itertools.cycle(working_keys)
            # Bug 6 fix: cap remaining attempts to the new (smaller) pool size
            attempts = min(attempts - 1, len(working_keys))
            logger.info(f"  [AI] → Failing over... {len(working_keys)} keys remaining in rotation.")
            continue
                
        except Exception as e:
            logger.error(f"  [AI] {provider.capitalize()} error: {e}")
            last_error = e
            if attempt < attempts - 1:
                logger.info("  [AI] → Failing over to next AI model/key due to error...")
                continue

    # If we get here, all failed
    return None


def _call_groq(api_key: str, system_prompt: str, user_prompt: str, max_tokens: int, masked_key: str, model_type: str) -> Optional[str]:
    """Call Groq API (Llama 3.3 70B — blazing fast)."""
    try:
        from groq import Groq

        model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        logger.debug(f"[AI] Calling Groq ({model}) using key {masked_key}")

        client = Groq(api_key=api_key)
        
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            model=model,
            max_tokens=max_tokens,
            temperature=0.7,
        )

        text = chat_completion.choices[0].message.content
        if not text:
            raise Exception("Groq returned empty response")
        
        logger.debug(f"[AI] Groq response received ({len(text)} chars)")
        return text.strip()

    except ImportError:
        logger.warning("[AI] 'groq' library not installed.")
        raise Exception("groq SDK not installed")
    except Exception as e:
        err_str = str(e).lower()
        if "429" in err_str or "rate_limit" in err_str or "quota" in err_str or "limit" in err_str:
            raise AILimitReached("Groq Rate Limit hit.")
        raise e


def _call_anthropic(api_key: str, system_prompt: str, user_prompt: str, max_tokens: int) -> Optional[str]:
    try:
        from anthropic import Anthropic, RateLimitError
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
        logger.warning("[AI] 'anthropic' library not installed.")
        raise Exception("anthropic SDK not installed")
    except Exception as e:
        err_str = str(e).lower()
        if "429" in err_str or "rate_limit" in err_str or "quota" in err_str:
            raise AILimitReached("Anthropic Rate Limit hit.")
        raise e


def _extract_gemini_text(response) -> Optional[str]:
    """Extract text from Gemini GenerateContentResponse with fallback shapes."""
    if response is None:
        return None

    text = None
    try:
        text = getattr(response, "text", None)
        if text:
            return str(text).strip()
    except Exception:
        pass

    try:
        candidates = getattr(response, "candidates", None)
        if candidates:
            first = candidates[0]
            content = getattr(first, "content", None)
            if content:
                parts = getattr(content, "parts", None)
                if parts:
                    return "".join(str(getattr(p, "text", "")) for p in parts).strip()
                return str(getattr(content, "text", "")).strip()
    except Exception:
        pass

    try:
        content = getattr(response, "content", None)
        if content:
            parts = getattr(content, "parts", None)
            if parts:
                return "".join(str(getattr(p, "text", "")) for p in parts).strip()
            return str(getattr(content, "text", "")).strip()
    except Exception:
        pass

    return None


def _call_gemini(api_key: str, system_prompt: str, user_prompt: str, max_tokens: int, response_format: str, masked_key: str, model_type: str) -> Optional[str]:
    try:
        from google import genai
        from google.genai import types
        from google.genai.errors import APIError

        client = genai.Client(api_key=api_key)

        config_kwargs = {
            "system_instruction": system_prompt,
            "temperature": 0.7,
            "max_output_tokens": max_tokens,
        }

        if response_format == "json":
            config_kwargs["response_mime_type"] = "application/json"
            config_kwargs["response_json_schema"] = {"type": "object"}

        config = types.GenerateContentConfig(**config_kwargs)

        model_name = _get_gemini_model(model_type)
        logger.debug(f"[AI] Calling Gemini ({model_name}) using key {masked_key}")
        response = client.models.generate_content(
            model=model_name,
            contents=user_prompt,
            config=config
        )

        text = _extract_gemini_text(response)
        if not text:
            raise Exception("Gemini returned empty response")
        return text

    except Exception as e:
        err_str = str(e).lower()
        if "429" in err_str or "quota" in err_str or "resource_exhausted" in err_str:
            raise AILimitReached("Gemini Free Tier Quota Exhausted.")
        raise e
