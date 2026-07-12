import os
import time
import sys
from selenium.webdriver.common.by import By
from utils.browser import create_driver

os.environ['HEADLESS'] = 'false'
url = 'https://www.linkedin.com/jobs/view/software-engineer-at-mailercloud-4427920806/'

if __name__ == '__main__':
    driver = create_driver()
    if not driver:
        raise SystemExit('Failed to create driver')
    try:
        driver.get(url)
        time.sleep(12)

        matches = driver.execute_script('''
            const nodes = [];
            const text = 'Easy Apply';
            const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT, null, false);
            while (walker.nextNode()) {
                const el = walker.currentNode;
                const txt = (el.textContent || '').trim();
                if (txt.includes(text)) {
                    const rect = el.getBoundingClientRect();
                    nodes.push({
                        tag: el.tagName,
                        text: txt.replace(/\s+/g, ' '),
                        role: el.getAttribute('role'),
                        ariaLabel: el.getAttribute('aria-label'),
                        className: el.className,
                        href: el.getAttribute('href'),
                        onclick: el.getAttribute('onclick'),
                        nodeType: el.nodeType,
                        xpath: getXPath(el),
                        parentTag: el.parentElement ? el.parentElement.tagName : null,
                        parentClass: el.parentElement ? el.parentElement.className : null,
                        parentHasOnclick: el.parentElement ? !!el.parentElement.getAttribute('onclick') : false,
                        parentHref: el.parentElement ? el.parentElement.getAttribute('href') : null,
                        parentRole: el.parentElement ? el.parentElement.getAttribute('role') : null,
                        parentTagName: el.parentElement ? el.parentElement.tagName : null,
                        rect: {width: rect.width, height: rect.height, x: rect.x, y: rect.y},
                    });
                    if (nodes.length >= 20) break;
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
            return nodes;
        ''')

        for i, m in enumerate(matches, 1):
            print(f'=== {i} ===')
            print('tag=', m['tag'])
            print('text=', m['text'].encode('ascii','backslashreplace').decode('ascii'))
            print('role=', m['role'])
            print('ariaLabel=', m['ariaLabel'])
            print('class=', m['className'])
            print('href=', m['href'])
            print('onclick=', m['onclick'])
            print('xpath=', m['xpath'])
            print('parentTag=', m['parentTag'], 'parentClass=', m['parentClass'])
            print('parentHref=', m['parentHref'])
            print('parentRole=', m['parentRole'])
            print('rect=', m['rect'])
    finally:
        driver.quit()
