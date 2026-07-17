"""Quick test to verify all configured Gemini API keys work."""
import os
from dotenv import load_dotenv
load_dotenv()

from google import genai
from google.genai import types

keys_str = os.getenv("GEMINI_API_KEY", "")
model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
keys = [k.strip() for k in keys_str.split(",") if k.strip()]

print(f"Found {len(keys)} key(s). Model: {model}")
print("=" * 50)

for i, key in enumerate(keys, 1):
    print(f"Testing Key {i} ({key[:12]}...):")
    try:
        client = genai.Client(api_key=key)
        response = client.models.generate_content(
            model=model,
            contents="What is 2+2? Reply with just the number.",
            config=types.GenerateContentConfig(max_output_tokens=50)
        )
        # Try .text first, fall back to candidates
        text = None
        try:
            text = response.text
        except Exception:
            pass
        if not text and response.candidates:
            try:
                text = response.candidates[0].content.parts[0].text
            except Exception:
                pass
        finish = None
        if response.candidates:
            finish = str(response.candidates[0].finish_reason)

        if text:
            print(f"  PASS - Replied: {repr(text.strip())}")
        else:
            print(f"  WARN - Connected but empty response (finish_reason={finish})")
    except Exception as e:
        err = str(e)
        if "429" in err or "quota" in err.lower():
            print(f"  FAIL - Quota exhausted (daily/minute limit hit)")
        elif "401" in err or "API_KEY" in err:
            print(f"  FAIL - Invalid API key")
        else:
            print(f"  FAIL - {err[:200]}")
    print()
