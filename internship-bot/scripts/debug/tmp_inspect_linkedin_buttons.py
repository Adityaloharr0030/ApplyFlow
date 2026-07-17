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
        time.sleep(8)
        print('current_url=', driver.current_url)
        print('title=', driver.title)
        buttons = driver.find_elements(By.TAG_NAME, 'button')
        print('total buttons=', len(buttons))
        for i, b in enumerate(buttons[:40], 1):
            try:
                txt = (b.text or '').strip()
                aria = b.get_attribute('aria-label')
                role = b.get_attribute('role')
                cls = b.get_attribute('class')
                outer = b.get_attribute('outerHTML') or ''
                if 'apply' in txt.lower() or 'apply' in (aria or '').lower() or 'Easy' in txt or 'Easy' in (aria or ''):
                    print('\n=== button', i, '===')
                    print('text=', repr(txt))
                    print('aria=', repr(aria))
                    print('role=', repr(role))
                    print('class=', repr(cls))
                    print('outer=', outer[:1200])
            except Exception as e:
                print('button', i, 'error', e)
        links = driver.find_elements(By.TAG_NAME, 'a')
        print('total links=', len(links))
        for i, a in enumerate(links[:80], 1):
            try:
                txt = (a.text or '').strip()
                href = a.get_attribute('href')
                role = a.get_attribute('role')
                cls = a.get_attribute('class')
                outer = a.get_attribute('outerHTML') or ''
                if 'apply' in txt.lower() or 'easy' in txt.lower() or 'jobs' in (href or '').lower():
                    print('\n=== anchor', i, '===')
                    print('text=', repr(txt))
                    print('href=', repr(href))
                    print('role=', repr(role))
                    print('class=', repr(cls))
                    print('outer=', outer[:1200])
            except Exception as e:
                print('link', i, 'error', e)
    finally:
        driver.quit()
