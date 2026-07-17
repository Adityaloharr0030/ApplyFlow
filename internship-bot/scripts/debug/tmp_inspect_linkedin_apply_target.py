import os
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from utils.browser import create_driver

def dump_el(el, prefix=''):
    print(f"{prefix}tag={el.tag_name} displayed={el.is_displayed()} enabled={el.is_enabled()}")
    print(f"{prefix}text={repr(el.text.strip())}")
    print(f"{prefix}attrs={el.get_attribute('class')} href={el.get_attribute('href')} role={el.get_attribute('role')}")
    outer = el.get_attribute('outerHTML') or ''
    print(f"{prefix}outerHTML={outer[:1200]}")

url = 'https://in.linkedin.com/jobs/view/software-engineer-at-mailercloud-4427920806'

os.environ['HEADLESS'] = 'false'

def main():
    driver = create_driver()
    if not driver:
        raise SystemExit('Failed to create driver')
    try:
        driver.get(url)
        time.sleep(10)
        print('current_url=', driver.current_url)
        print('title=', driver.title)

        # search for text nodes containing Easy Apply
        xpath = "//*[contains(translate(normalize-space(string(.)), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'easy apply')]"
        els = driver.find_elements(By.XPATH, xpath)
        print('total easy apply matches=', len(els))
        for idx, el in enumerate(els[:20], 1):
            print('\n=== match', idx, '===')
            dump_el(el)
            # clickable ancestor
            try:
                anc = el.find_element(By.XPATH, "ancestor::button|ancestor::a|ancestor::*[@role='button']")
                print('clickable ancestor:')
                dump_el(anc, '  ')
            except Exception as e:
                print('no clickable ancestor:', e)
    finally:
        driver.quit()

if __name__ == '__main__':
    main()
