import re

path = 'tmp_linkedin_page.html'
with open(path, 'r', encoding='utf-8') as f:
    html = f.read()

pattern = re.compile(r'.{0,300}(Easy Apply|easy apply).{0,300}', re.DOTALL)
matches = pattern.findall(html)
print('matches:', len(matches))
for m in pattern.finditer(html):
    start = max(0, m.start() - 300)
    end = min(len(html), m.end() + 300)
    snippet = html[start:end]
    print('='*80)
    print(snippet)
    print('\n')
