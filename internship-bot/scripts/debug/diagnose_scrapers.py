"""Diagnostic script to check Internshala + LetsInternship HTML structure."""
import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

print("=" * 60)
print("INTERNSHALA DIAGNOSTIC")
print("=" * 60)
try:
    r = requests.get("https://internshala.com/internships/computer-science-internship", headers=HEADERS, timeout=15)
    print(f"Status: {r.status_code}")
    soup = BeautifulSoup(r.text, "html.parser")
    print(f"Title: {soup.title.string if soup.title else 'No title'}")
    
    # Check for JS-rendered page
    body_text = soup.body.get_text(strip=True)[:500] if soup.body else ""
    print(f"Body text (first 500 chars): {body_text[:500]}")
    
    # Try finding cards
    selectors_to_try = [
        ".individual_internship",
        ".internship_meta",
        "div[class*='internship_']",
        ".container-fluid",
        "a[href*='/internship/detail/']",
    ]
    for sel in selectors_to_try:
        found = soup.select(sel)
        print(f"  Selector '{sel}': {len(found)} matches")
    
    # Print first card-like element
    detail_links = soup.select("a[href*='/internship/detail/']")
    if detail_links:
        print(f"\nFirst detail link: {detail_links[0].get('href')}")
        parent = detail_links[0].parent
        while parent and parent.name != "body":
            classes = parent.get("class", [])
            if classes:
                print(f"  Parent: <{parent.name}> class={classes}")
                # Print this container's HTML
                if any("internship" in c.lower() for c in classes):
                    print(f"\n--- INTERNSHIP CARD HTML (first 2000 chars) ---")
                    print(parent.prettify()[:2000])
                    break
            parent = parent.parent
    else:
        print("No /internship/detail/ links found - page may be JS-rendered")
        print(f"\nPage text snippet: {body_text[:1000]}")

except Exception as e:
    print(f"ERROR: {e}")

print("\n" + "=" * 60)
print("LETSINTERNSHIP DIAGNOSTIC")  
print("=" * 60)
try:
    r = requests.get("https://www.letsintern.com/internships", headers=HEADERS, timeout=15)
    print(f"Status: {r.status_code}")
    soup = BeautifulSoup(r.text, "html.parser")
    print(f"Title: {soup.title.string if soup.title else 'No title'}")
    
    body_text = soup.body.get_text(strip=True)[:500] if soup.body else ""
    print(f"Body text (first 500 chars): {body_text[:500]}")
    
    selectors_to_try = [
        ".internship-card",
        ".internship-listing",
        ".listing-card",
        ".card",
        "a[href*='/internship/']",
        "a[href*='/apply/']",
    ]
    for sel in selectors_to_try:
        found = soup.select(sel)
        print(f"  Selector '{sel}': {len(found)} matches")
    
    # Print all unique class names
    classes_seen = set()
    for tag in soup.find_all(True):
        for c in (tag.get("class") or []):
            classes_seen.add(c)
    
    internship_classes = [c for c in sorted(classes_seen) if "intern" in c.lower() or "card" in c.lower() or "list" in c.lower() or "job" in c.lower()]
    print(f"\nRelevant classes found: {internship_classes}")

except Exception as e:
    print(f"ERROR: {e}")
