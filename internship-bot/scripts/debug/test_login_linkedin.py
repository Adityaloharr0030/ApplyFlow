import os
import time
from utils.browser import create_driver
from selenium.webdriver.common.by import By

os.environ['HEADLESS'] = 'false'

if __name__ == '__main__':
    driver = create_driver()
    if not driver:
        raise SystemExit('Driver creation failed')

    try:
        print('Opening LinkedIn login page...')
        driver.get('https://www.linkedin.com/login')
        time.sleep(8)

        selectors = [
            "input[autocomplete='username']",
            "input[autocomplete='username webauthn']",
            "input[type='email'][autocomplete*='username']",
            "input[autocomplete='current-password']",
            "input[type='password']",
            "button[type='submit']",
            "button",
        ]

        for sel in selectors:
            els = driver.find_elements(By.CSS_SELECTOR, sel)
            print(f'SELECTOR {sel} found', len(els))
            for i, el in enumerate(els, 1):
                try:
                    print(' ', i, 'visible', el.is_displayed(), 'enabled', el.is_enabled(), 'type', el.get_attribute('type'), 'name', el.get_attribute('name'), 'id', el.get_attribute('id'), 'text', repr(el.text))
                except Exception as e:
                    print(' ', i, 'error', e)

        print('Testing _wait_and_find email field...')
        from platforms.login import _wait_and_find, _find_button_by_text
        email = _wait_and_find(driver, "input[autocomplete='username'], input[autocomplete='username webauthn'], input[type='email'][autocomplete*='username']", timeout=15)
        print('email element', email, 'displayed' if email and email.is_displayed() else 'hidden')

        password = _wait_and_find(driver, "input[autocomplete='current-password'], input[type='password']", timeout=15)
        print('password element', password, 'displayed' if password and password.is_displayed() else 'hidden')

        btn = _wait_and_find(driver, "button[type='submit']", timeout=10)
        print('submit button', btn, 'displayed' if btn and btn.is_displayed() else 'hidden')

        text_btn = _find_button_by_text(driver, ["sign in"], timeout=10)
        print('text-based sign-in button', text_btn, 'text', text_btn.text if text_btn else None)

        text_btn_with = _find_button_by_text(driver, ["sign in with"], timeout=10)
        print('text-based sign-in-with button', text_btn_with, 'text', text_btn_with.text if text_btn_with else None)

    finally:
        driver.quit()
