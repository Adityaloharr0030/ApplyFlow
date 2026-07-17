import os
import time
from selenium.webdriver.common.by import By
from utils.browser import create_driver

os.environ['HEADLESS'] = 'false'
url = 'https://in.linkedin.com/jobs/view/software-engineer-at-mailercloud-4427920806'

if __name__ == '__main__':
    driver = create_driver()
    if not driver:
        raise SystemExit('Failed to create driver')
    try:
        driver.get(url)
        time.sleep(10)
        print('current_url=', driver.current_url)
        print('title=', driver.title)

        candidates = []
        xpath = "//*[contains(translate(normalize-space(string(.)), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'apply')]"
        els = driver.find_elements(By.XPATH, xpath)
        print('total apply matches=', len(els))
        for e in els:
            try:
                text = (e.text or '').strip()
                if not text:
                    continue
                if len(text) > 120:
                    continue
                if not e.is_displayed():
                    continue
                tag = e.tag_name
                href = e.get_attribute('href')
                role = e.get_attribute('role')
                cls = e.get_attribute('class')
                outer = e.get_attribute('outerHTML') or ''
                candidates.append((tag, text, role, href, cls, outer[:1000]))
            except Exception:
                continue
        print('filtered candidates=', len(candidates))
        for i, (tag, text, role, href, cls, outer) in enumerate(candidates[:50], 1):
            print('\n=== candidate', i, '===')
            print('tag=', tag)
            print('text=', repr(text))
            print('role=', repr(role), 'href=', repr(href))
            print('class=', repr(cls))
            print('outerHTML=', outer)
    finally:
        driver.quit()
