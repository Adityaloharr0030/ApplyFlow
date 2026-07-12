import os
import time
from utils.browser import create_driver

os.environ['HEADLESS'] = 'false'

url = 'https://in.linkedin.com/jobs/view/software-engineer-at-mailercloud-4427920806'

def main():
    driver = create_driver()
    if not driver:
        raise SystemExit('Failed to create driver')
    try:
        driver.get(url)
        time.sleep(10)
        print('current_url=', driver.current_url)
        print('title=', driver.title)

        print('\n--- XPATH easy apply elements ---')
        els = driver.find_elements('xpath', "//*[contains(translate(normalize-space(string(.)), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'easy apply')]")
        print('count=', len(els))
        for i, e in enumerate(els, 1):
            print('---', i)
            print('tag=', e.tag_name)
            print('text=', repr(e.text.strip()))
            print('displayed=', e.is_displayed(), 'enabled=', e.is_enabled())
            outer = e.get_attribute('outerHTML')
            print(outer[:1200])
            print()

        print('\n--- BUTTON elements with Easy Apply text ---')
        buttons = driver.find_elements('xpath', "//button[contains(translate(normalize-space(string(.)), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'easy apply')]")
        print('button count=', len(buttons))
        for i, b in enumerate(buttons, 1):
            print('---', i)
            print('text=', repr(b.text.strip()))
            print('displayed=', b.is_displayed(), 'enabled=', b.is_enabled())
            print(b.get_attribute('outerHTML')[:1200])
            print()

    finally:
        driver.quit()

if __name__ == '__main__':
    main()
