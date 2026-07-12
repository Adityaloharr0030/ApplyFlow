import os
import time
from utils.browser import create_driver
from selenium.webdriver.common.by import By

os.environ['HEADLESS'] = 'false'

url = 'https://in.linkedin.com/jobs/view/software-engineer-at-mailercloud-4427920806'

def show_snippet(src, token, radius=120):
    idx = src.find(token)
    if idx == -1:
        return
    start = max(0, idx - radius)
    end = min(len(src), idx + len(token) + radius)
    print('\n--- snippet for', token, '---')
    print(src[start:end].replace('\n',' '))


def main():
    driver = create_driver()
    if not driver:
        raise SystemExit('Failed to create driver')
    try:
        driver.get(url)
        time.sleep(10)
        src = driver.page_source.lower()
        show_snippet(src, 'easy apply')
        show_snippet(src, 'jobs-apply-button')
        show_snippet(src, 'data-control-name')
        show_snippet(src, 'data-test-apply')
        show_snippet(src, 'apply now')
        show_snippet(src, 'apply as a network')
        show_snippet(src, 'easy apply')
        print('\n--- Elements containing easy apply or apply ---')
        elems = driver.find_elements(By.XPATH, "//*[contains(translate(normalize-space(string(.)), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'easy apply') or contains(translate(normalize-space(string(.)), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'apply')]")
        print('elements count=', len(elems))
        seen = set()
        for i, e in enumerate(elems[:80], 1):
            text = e.text.strip()
            if text.lower() in seen:
                continue
            seen.add(text.lower())
            print('---', i, 'tag=', e.tag_name, 'text=', repr(text), 'disp=', e.is_displayed(), 'en=', e.is_enabled())
            outer = e.get_attribute('outerHTML')
            print(outer[:1200])
            print()
    finally:
        driver.quit()

if __name__ == '__main__':
    main()
