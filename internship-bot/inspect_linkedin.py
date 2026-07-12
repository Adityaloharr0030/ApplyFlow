from utils.browser import create_driver
import time
from selenium.webdriver.common.by import By

if __name__ == '__main__':
    import os
    os.environ['HEADLESS'] = 'false'

    driver = create_driver()
    if not driver:
        raise SystemExit('Failed to create driver')

    try:
        driver.get('https://www.linkedin.com/login')
        time.sleep(7)
        print('current_url=', driver.current_url)
        print('title=', driver.title)

        email_selectors = [
            "input#username",
            "input[name='session_key']",
            "input[autocomplete='username']",
            "input[type='text'][name*='email']",
        ]
        for sel in email_selectors:
            els = driver.find_elements(By.CSS_SELECTOR, sel)
            print(f"EMAIL SEL={sel} count={len(els)}")
            for i, el in enumerate(els, 1):
                print(i, 'displayed', el.is_displayed(), 'enabled', el.is_enabled(), 'type', el.get_attribute('type'), 'name', el.get_attribute('name'), 'id', el.get_attribute('id'))
                print(el.get_attribute('outerHTML')[:400])

        password_selectors = [
            "input#password",
            "input[name='session_password']",
            "input[type='password']",
            "input[autocomplete='current-password']",
        ]
        for sel in password_selectors:
            els = driver.find_elements(By.CSS_SELECTOR, sel)
            print(f"PASSWORD SEL={sel} count={len(els)}")
            for i, el in enumerate(els, 1):
                print(i, 'displayed', el.is_displayed(), 'enabled', el.is_enabled(), 'type', el.get_attribute('type'), 'name', el.get_attribute('name'), 'id', el.get_attribute('id'))
                print(el.get_attribute('outerHTML')[:400])

        btn_selectors = [
            "button[type='submit']",
            "button.btn__primary--large",
            "button[aria-label='Sign in']",
            "button[data-litms-control-urn='login-submit']",
            "button[data-tracking-control-name='login_submit']",
        ]
        for sel in btn_selectors:
            els = driver.find_elements(By.CSS_SELECTOR, sel)
            print(f"BUTTON SEL={sel} count={len(els)}")
            for i, el in enumerate(els, 1):
                print(i, 'text', repr(el.text), 'displayed', el.is_displayed(), 'enabled', el.is_enabled())
                print(el.get_attribute('outerHTML')[:400])

        print('page_source begins:')
        print(driver.page_source[:2000])
    finally:
        driver.quit()
