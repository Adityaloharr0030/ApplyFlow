from bs4 import BeautifulSoup

path = 'tmp_linkedin_page.html'
with open(path, 'r', encoding='utf-8') as f:
    soup = BeautifulSoup(f, 'html.parser')

for i, tag in enumerate(soup.find_all(string=lambda t: 'easy apply' in t.lower()), 1):
    print('='*80)
    print('MATCH', i)
    text = tag.strip()
    print('text:', repr(text))
    node = tag.parent
    for depth in range(5):
        if node is None:
            break
        print(f'depth {depth}: {node.name}', node.attrs)
        if node.name in ['button', 'a', 'span', 'div', 'li']:
            snippet = str(node)[:2000]
            print('snippet:', snippet)
        node = node.parent
    print()