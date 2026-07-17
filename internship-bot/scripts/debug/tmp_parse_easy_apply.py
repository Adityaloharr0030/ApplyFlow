from bs4 import BeautifulSoup

path = 'tmp_linkedin_page.html'
with open(path, 'r', encoding='utf-8') as f:
    soup = BeautifulSoup(f, 'html.parser')

matches = []
for tag in soup.find_all(text=lambda t: 'easy apply' in t.lower()):
    parent = tag.parent
    matches.append((tag, parent, parent.name, parent.attrs))

print('found', len(matches), 'matches')
for i, (text, parent, name, attrs) in enumerate(matches, 1):
    print('='*80)
    print('match', i)
    print('text:', repr(text.strip()))
    print('parent tag:', name)
    print('parent attrs:', attrs)
    print('parent html snippet:')
    print(parent.prettify()[:2000])
    print()