"""Quick verification of all scrapers and core modules."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import json

# CHECK 4 - Internshala
print("=" * 60)
print("CHECK 4: Internshala Scraper")
print("=" * 60)
try:
    from scraper.internshala import scrape_internshala
    p = json.load(open('data/profile.json', encoding='utf-8'))
    results = scrape_internshala(p)
    print(f"Internshala: {len(results)} listings found")
    for r in results[:3]:
        print(f"  {r['title']} @ {r['company']} ({r['location']}) - {r.get('stipend', 'N/A')}")
    if not results:
        print("ZERO results -- CSS selectors need updating (BUG 6)")
except Exception as e:
    print(f"ERROR: {e}")

# CHECK 5 - LinkedIn
print("\n" + "=" * 60)
print("CHECK 5: LinkedIn Scraper")
print("=" * 60)
try:
    from scraper.linkedin import scrape_linkedin
    results = scrape_linkedin(p)
    print(f"LinkedIn: {len(results)} listings found")
    for r in results[:3]:
        print(f"  {r['title']} @ {r['company']} ({r['location']})")
except Exception as e:
    print(f"ERROR: {e}")

# CHECK - LetsInternship
print("\n" + "=" * 60)
print("CHECK: LetsInternship Scraper")
print("=" * 60)
try:
    from scraper.letsinternship import scrape_letsinternship
    results = scrape_letsinternship(p)
    print(f"LetsInternship: {len(results)} listings found")
    if not results:
        print("Expected: 0 results (site is no longer active)")
except Exception as e:
    print(f"ERROR: {e}")

# CHECK 6 - AI Scoring
print("\n" + "=" * 60)
print("CHECK 6: AI Scoring")
print("=" * 60)
try:
    from agent.filter import filter_listings
    test = [
        {'title': 'Flutter Developer Intern', 'company': 'TechCorp', 'location': 'Remote',
         'apply_url': 'https://example.com/1', 'source': 'internshala'},
        {'title': 'Java Backend Intern', 'company': 'OldBank Ltd', 'location': 'Pune',
         'apply_url': 'https://example.com/2', 'source': 'internshala'},
    ]
    approved = filter_listings(test, p)
    print(f"Approved {len(approved)}/2 listings")
    for a in approved:
        print(f"  -> {a['title']} -- score {a['score']} -- {a['reason']}")
except Exception as e:
    print(f"ERROR: {e}")

# CHECK 7 - Cover Note
print("\n" + "=" * 60)
print("CHECK 7: Cover Note Generation")
print("=" * 60)
try:
    from agent.cover_note import generate_cover_note
    note = generate_cover_note({'title': 'Flutter Intern', 'company': 'Startup X'}, p)
    print("Cover note preview:")
    print(note[:300])
    if len(note) > 300:
        print("...")
except Exception as e:
    print(f"ERROR: {e}")

# CHECK 8 - CSV Logger
print("\n" + "=" * 60)
print("CHECK 8: CSV Logger")
print("=" * 60)
try:
    from tracker.sheets import log_application
    listing = {'title': 'Test Role', 'company': 'Test Corp', 'location': 'Remote',
               'source': 'internshala', 'apply_url': 'https://test.com', 'score': 7}
    log_application(listing, 'Applied', 'This is a test cover note.')
    print("CSV logger: OK -- check logs/applications.csv")
except Exception as e:
    print(f"ERROR: {e}")

print("\n" + "=" * 60)
print("ALL CHECKS COMPLETE")
print("=" * 60)
