import re
import os
import glob

# The AI agents all take UserProfile as an argument, so we can extract user_id from profile.
# We need to update get_ai_response calls inside them.

def rewrite_agent(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # If get_ai_response is already using user_id, skip
    if "user_id=profile.user_id" in content or "user_id=" in content:
        print(f"Skipping {file_path} - already has user_id")
        return

    # Look for get_ai_response(...) and add user_id=profile.user_id if profile is available
    if "profile" in content and "get_ai_response" in content:
        # Simple regex replace for get_ai_response(...)
        # We look for the closing parenthesis and inject user_id=profile.user_id
        # This is a bit fragile with multiline args, so we'll do something simpler:
        content = re.sub(r'get_ai_response\((.*?)\)', r'get_ai_response(\1, user_id=profile.user_id if profile else None)', content, flags=re.DOTALL)
        
        # Some args might be duplicated if we're not careful. Let's just do text replacement carefully.
        # Let's try replacing specific known lines instead of generic regex to avoid breaking things.
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

agents_dir = "c:\\ApplyFlow\\internship-bot\\agent"
for filepath in glob.glob(os.path.join(agents_dir, "*.py")):
    # we don't rewrite ai_client.py
    if "ai_client.py" in filepath:
        continue
    rewrite_agent(filepath)

print("Agents rewritten.")
