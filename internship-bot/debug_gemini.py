"""Quick debug script to test Gemini API key"""
import os
from dotenv import load_dotenv
load_dotenv()

api_key_str = os.getenv("GEMINI_API_KEY", "")
api_key = api_key_str.split(",")[0].strip() if api_key_str else ""
print(f"API Key (first 10 chars): {api_key[:10]}...")
print(f"API Key length: {len(api_key)}")

from google import genai as google_genai
from google.genai import types as genai_types

client = google_genai.Client(api_key=api_key)

# Test 1: List available models
print("\n--- Available Models ---")
try:
    for model in client.models.list():
        if "flash" in model.name.lower() or "gemini" in model.name.lower():
            print(f"  {model.name}")
except Exception as e:
    print(f"  Error listing models: {e}")

# Test 2: Try different model names
test_models = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-1.5-flash",
    "gemini-flash-latest",
    "models/gemini-2.0-flash",
]

print("\n--- Testing Each Model ---")
for model_name in test_models:
    try:
        response = client.models.generate_content(
            model=model_name,
            contents="Say hello in one word.",
            config=genai_types.GenerateContentConfig(max_output_tokens=20)
        )
        # Debug the full response
        text = None
        try:
            text = response.text
        except Exception:
            pass
        
        candidates = getattr(response, 'candidates', None)
        print(f"\n  Model: {model_name}")
        print(f"    .text = {repr(text)}")
        print(f"    .candidates = {candidates}")
        if candidates:
            for i, c in enumerate(candidates):
                print(f"    candidate[{i}].finish_reason = {getattr(c, 'finish_reason', '?')}")
                content = getattr(c, 'content', None)
                if content:
                    parts = getattr(content, 'parts', [])
                    for j, p in enumerate(parts):
                        print(f"    candidate[{i}].content.parts[{j}].text = {repr(getattr(p, 'text', '?'))}")
        
        if text:
            print(f"    >>> SUCCESS: \"{text.strip()}\"")
            break
    except Exception as e:
        print(f"  Model: {model_name} -> ERROR: {e}")
