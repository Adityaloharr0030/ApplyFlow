from dotenv import load_dotenv
load_dotenv()
import json
from agent.cover_note import generate_cover_note
from agent.filter import score_listing

profile = json.load(open("data/profile.json"))

listing = {
    "title": "Flutter Developer Intern",
    "company": "TechStartup Pvt Ltd",
    "location": "Remote",
    "stipend": "10000/month",
    "duration": "3 months",
    "description": "We are looking for a Flutter developer with Firebase and REST API experience.",
    "source": "internshala",
    "apply_url": "https://internshala.com/internship/detail/test",
}

print("--- Cover Note ---")
note = generate_cover_note(listing, profile)
print(note[:500])
print("...")

print()
print("--- AI Score ---")
result = score_listing(listing, profile)
print(f"Score: {result['score']}/10")
print(f"Apply: {result['apply']}")
print(f"Reason: {result['reason']}")
