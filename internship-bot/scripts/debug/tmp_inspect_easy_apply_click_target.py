import os
import time
from selenium.webdriver.common.by import By
from utils.browser import create_driver

os.environ['HEADLESS'] = 'false'
url = 'https://www.linkedin.com/jobs/view/software-engineer-at-mailercloud-4427920806/'

SCRIPT = '''
const results = [];
const text = 'Easy Apply';
const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT, null, false);
while (walker.nextNode()) {
    const el = walker.currentNode;
    const txt = (el.textContent || '').trim();
    if (txt === text || txt.includes(text)) {
        let node = el;
        let block = [];
        const path = [];
        while (node && node.nodeType === Node.ELEMENT_NODE) {
            const info = {
                tag: node.tagName,
                text: (node.textContent || '').trim().replace(/\s+/g, ' '),
                role: node.getAttribute('role'),
                ariaLabel: node.getAttribute('aria-label'),
                className: node.className,
                href: node.getAttribute('href'),
                onclick: node.getAttribute('onclick'),
                type: node.getAttribute('type'),
                nodeName: node.nodeName,
                xpath: null,
            };
            path.push(info);
            if (['A', 'BUTTON'].includes(node.tagName) || node.onclick || node.getAttribute('role') === 'button') {
                break;
            }
            node = node.parentElement;
        }
        results.push({
            text: txt.replace(/\s+/g, ' '),
            nodeTag: el.tagName,
            nodeClass: el.className,
            nodeXPath: getXPath(el),
            path: path.map((p) => ({tag: p.tag, text: p.text, role: p.role, ariaLabel: p.ariaLabel, className: p.className, href: p.href, onclick: p.onclick, type: p.type}))
        });
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
return results;
'''

if __name__ == '__main__':
    driver = create_driver()
    if not driver:
        raise SystemExit('Failed to create driver')
    try:
        driver.get(url)
        time.sleep(12)
        results = driver.execute_script(SCRIPT)
        print('Found', len(results), 'Easy Apply node(s)')
        for i, r in enumerate(results, 1):
            print(f'=== result {i} ===')
            print('text=', repr(r['text']))
            print('nodeTag=', r['nodeTag'])
            print('nodeClass=', repr(r['nodeClass']))
            print('nodeXPath=', r['nodeXPath'])
            for j, p in enumerate(r['path'], 1):
                print(f'  path[{j}] tag={p["tag"]} href={repr(p["href"])} onclick={repr(p["onclick"]))} role={repr(p["role"]))} type={repr(p["type"]))} class={repr(p["className"]))} text={repr(p["text"]))}')
    finally:
        driver.quit()
