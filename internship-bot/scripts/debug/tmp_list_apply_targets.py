import os
import time
from utils.browser import create_driver

os.environ['HEADLESS'] = 'false'
url = 'https://www.linkedin.com/jobs/view/software-engineer-at-mailercloud-4427920806/'

SCRIPT = r'''
(function() {
  const result = [];
  const text = 'easy apply';
  const elements = Array.from(document.querySelectorAll('button, a, [role="button"], div, span, p'));
  for (const el of elements) {
    const txt = (el.innerText || '').trim();
    if (!txt) continue;
    const lower = txt.toLowerCase();
    if (lower.includes(text) || lower.includes('apply') || lower.includes('submit application')) {
      const rect = el.getBoundingClientRect();
      if (rect.width === 0 && rect.height === 0) continue;
      const xpath = getXPath(el);
      result.push({
        tag: el.tagName,
        text: txt.replace(/\s+/g, ' '),
        role: el.getAttribute('role'),
        ariaLabel: el.getAttribute('aria-label'),
        className: el.className,
        href: el.href || null,
        onclick: el.getAttribute('onclick'),
        xpath: xpath,
        visible: rect.width > 0 && rect.height > 0,
        rect: {x: rect.x, y: rect.y, width: rect.width, height: rect.height},
      });
      if (result.length >= 50) break;
    }
  }
  function getXPath(node) {
    if (node.id) return 'id("' + node.id + '")';
    const comps = [];
    while (node && node.nodeType === 1) {
      let count = 1;
      let sibling = node.previousSibling;
      while (sibling) {
        if (sibling.nodeType === 1 && sibling.nodeName === node.nodeName) count++;
        sibling = sibling.previousSibling;
      }
      comps.unshift(node.nodeName.toLowerCase() + '[' + count + ']');
      node = node.parentNode;
    }
    return '/' + comps.join('/');
  }
  return result;
})();
'''

if __name__ == '__main__':
    driver = create_driver()
    if not driver:
        raise SystemExit('Failed to create driver')
    try:
        driver.get(url)
        time.sleep(15)
        print('readyState=', driver.execute_script('return document.readyState'))
        results = driver.execute_script(SCRIPT)
        print('results:', len(results))
        for i, r in enumerate(results, 1):
            print(f'=== {i} ===')
            print('tag=', r['tag'])
            print('text=', r['text'])
            print('role=', r['role'])
            print('ariaLabel=', r['ariaLabel'])
            print('class=', r['className'])
            print('href=', r['href'])
            print('onclick=', r['onclick'])
            print('xpath=', r['xpath'])
            print('rect=', r['rect'])
    finally:
        driver.quit()
