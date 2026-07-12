import os
import time
from selenium.webdriver.common.by import By
from utils.browser import create_driver

os.environ['HEADLESS'] = 'false'
url = 'https://www.linkedin.com/jobs/view/software-engineer-at-mailercloud-4427920806/'

SCRIPT = '''
const matches = [];
const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT, null, false);
while(walker.nextNode()) {
    const el = walker.currentNode;
    const text = (el.textContent || '').trim();
    if (text.includes('Easy Apply')) {
        const rect = el.getBoundingClientRect();
        const xpath = getXPath(el);
        const tag = el.tagName;
        const cls = el.className;
        const role = el.getAttribute('role');
        const aria = el.getAttribute('aria-label');
        const onclick = el.getAttribute('onclick');
        const href = el.getAttribute('href');
        const dataTest = el.getAttribute('data-control-name');
        const parent = el.parentElement ? el.parentElement.tagName + '[' + (el.parentElement.className || '').slice(0,50) + ']' : null;
        matches.push({tag, text: text.replace(/\s+/g,' '), role, aria, cls, href, onclick, dataTest, xpath, parent, rect: {width: rect.width, height: rect.height, x: rect.x, y: rect.y}});
        if (matches.length >= 25) break;
    }
}
function getXPath(node) {
    if (node.id) return 'id("' + node.id + '")';
    const parts = [];
    while(node && node.nodeType === Node.ELEMENT_NODE) {
        let index = 1;
        let sibling = node.previousSibling;
        while(sibling) {
            if (sibling.nodeType === Node.ELEMENT_NODE && sibling.nodeName === node.nodeName) index++;
            sibling = sibling.previousSibling;
        }
        parts.unshift(node.nodeName.toLowerCase() + '[' + index + ']');
        node = node.parentNode;
    }
    return '/' + parts.join('/');
}
return matches;
'''

if __name__ == '__main__':
    driver = create_driver()
    if not driver:
        raise SystemExit('Failed to create driver')
    try:
        driver.get(url)
        time.sleep(10)
        matches = driver.execute_script(SCRIPT)
        print(f'Found {len(matches)} matching elements')
        for i, m in enumerate(matches, 1):
            print(f'=== {i} ===')
            print('tag=', m['tag'])
            print('text=', repr(m['text']))
            print('role=', repr(m['role']))
            print('aria=', repr(m['aria']))
            print('class=', repr(m['cls']))
            print('href=', repr(m['href']))
            print('onclick=', repr(m['onclick']))
            print('data-control-name=', repr(m['dataTest']))
            print('xpath=', m['xpath'])
            print('parent=', m['parent'])
            print('rect=', m['rect'])
    finally:
        driver.quit()
