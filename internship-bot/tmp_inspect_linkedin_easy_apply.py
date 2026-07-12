import os
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from utils.browser import create_driver

os.environ['HEADLESS'] = 'false'
url = 'https://www.linkedin.com/jobs/view/software-engineer-at-mailercloud-4427920806/'

if __name__ == '__main__':
    driver = create_driver()
    if not driver:
        raise SystemExit('Failed to create driver')
    try:
        driver.get(url)
        time.sleep(10)

        def find_text_nodes(text):
            js = '''
            const text = arguments[0].toLowerCase();
            const nodes = [];
            const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT, null, false);
            while(walker.nextNode()) {
                const el = walker.currentNode;
                const txt = el.textContent || '';
                if (txt.toLowerCase().includes(text)) {
                    nodes.push(el);
                }
            }
            return nodes.slice(0, 40).map(el => ({
                tag: el.tagName,
                text: el.textContent.trim().replace(/\s+/g, ' '),
                role: el.getAttribute('role'),
                ariaLabel: el.getAttribute('aria-label'),
                className: el.className,
                outerHTML: el.outerHTML.slice(0, 1200),
                xpath: getXPath(el)
            }));
            function getXPath(node) {
                if (node.id) {
                    return 'id("' + node.id + '")';
                }
                const parts = [];
                while (node && node.nodeType === Node.ELEMENT_NODE) {
                    let index = 1;
                    let sibling = node.previousSibling;
                    while (sibling) {
                        if (sibling.nodeType === Node.ELEMENT_NODE && sibling.nodeName === node.nodeName) {
                            index++;
                        }
                        sibling = sibling.previousSibling;
                    }
                    const tagName = node.nodeName.toLowerCase();
                    parts.unshift(tagName + '[' + index + ']');
                    node = node.parentNode;
                }
                return '/' + parts.join('/');
            }
            '''
            return driver.execute_script(js, text)

        matches = driver.execute_script('''
            const text = arguments[0].toLowerCase();
            const nodes = [];
            const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT, null, false);
            while(walker.nextNode()) {
                const el = walker.currentNode;
                const txt = (el.textContent || '').toLowerCase();
                if (txt.includes(text)) {
                    nodes.push(el);
                }
            }
            return nodes.slice(0, 40).map(el => ({
                tag: el.tagName,
                text: (el.textContent || '').trim().replace(/\s+/g, ' '),
                role: el.getAttribute('role'),
                ariaLabel: el.getAttribute('aria-label'),
                className: el.className,
                outerHTML: el.outerHTML.slice(0, 1200),
                xpath: function() {
                    let node = el;
                    if (node.id) return 'id("' + node.id + '")';
                    const parts = [];
                    while (node && node.nodeType === Node.ELEMENT_NODE) {
                        let index = 1;
                        let sibling = node.previousSibling;
                        while (sibling) {
                            if (sibling.nodeType === Node.ELEMENT_NODE && sibling.nodeName === node.nodeName) index++;
                            sibling = sibling.previousSibling;
                        }
                        parts.unshift(node.nodeName.toLowerCase() + '[' + index + ']');
                        node = node.parentNode;
                    }
                    return '/' + parts.join('/');
                }()
            }));
        ''', 'Easy Apply')

        print('Found', len(matches), 'nodes containing Easy Apply')
        for i, m in enumerate(matches, 1):
            print(f'\n=== Node {i} ===')
            print('tag=', m['tag'])
            print('text=', repr(m['text']))
            print('role=', repr(m['role']))
            print('ariaLabel=', repr(m['ariaLabel']))
            print('class=', repr(m['className']))
            print('xpath=', m['xpath'])
            print('outerHTML=', m['outerHTML'])

        # also try near text by js query selector for exact button text
        els = driver.find_elements(By.XPATH, '//*[contains(normalize-space(.), "Easy Apply")]')
        print('XPath count', len(els))
        for i, el in enumerate(els[:40], 1):
            print(f'--- XPath {i} ---', el.tag_name, el.text)
    finally:
        driver.quit()
