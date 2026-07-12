import os
import time
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
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
        elems = driver.find_elements(By.XPATH, "//*[contains(normalize-space(.), 'Easy Apply')]")
        print('Found', len(elems), 'elements with Easy Apply text')
        for i, el in enumerate(elems, 1):
            try:
                txt = el.text.strip()
            except StaleElementReferenceException:
                print('===', i, 'stale element')
                continue
            print('===', i, 'tag=', el.tag_name, 'text=', repr(txt[:200]))
            print('  class=', el.get_attribute('class'))
            print('  role=', el.get_attribute('role'))
            print('  aria=', el.get_attribute('aria-label'))
            print('  href=', el.get_attribute('href'))
            try:
                a = el.find_element(By.XPATH, 'ancestor::a[1]')
                print('  ancestor a tag=', a.tag_name)
                print('  ancestor a class=', a.get_attribute('class'))
                print('  ancestor a href=', a.get_attribute('href'))
            except NoSuchElementException:
                print('  no ancestor a')
            try:
                btn = el.find_element(By.XPATH, 'ancestor::button[1]')
                print('  ancestor button tag=', btn.tag_name)
                print('  ancestor button class=', btn.get_attribute('class'))
                print('  ancestor button text=', repr(btn.text.strip()))
            except NoSuchElementException:
                print('  no ancestor button')
            try:
                ancestor = el.find_element(By.XPATH, '(ancestor::*[self::a or self::button or @role="button"])[1]')
                print('  clickable ancestor=', ancestor.tag_name)
                print('    class=', ancestor.get_attribute('class'))
                print('    href=', ancestor.get_attribute('href'))
                print('    role=', ancestor.get_attribute('role'))
                print('    text=', repr(ancestor.text.strip()[:200]))
            except NoSuchElementException:
                print('  no clickable ancestor')
    finally:
        driver.quit()
