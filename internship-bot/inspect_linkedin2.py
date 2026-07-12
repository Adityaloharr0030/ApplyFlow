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
        time.sleep(10)
        print('current_url=', driver.current_url)
        print('title=', driver.title)

        inputs = driver.find_elements(By.CSS_SELECTOR, 'input')
        print('TOTAL input count', len(inputs))
        for i, el in enumerate(inputs, 1):
            visible = el.is_displayed()
            enabled = el.is_enabled()
            print(f'INPUT {i}: visible={visible} enabled={enabled} type={el.get_attribute("type")} name={el.get_attribute("name")} id={el.get_attribute("id")} aria-label={el.get_attribute("aria-label")} placeholder={el.get_attribute("placeholder")} autocomplete={el.get_attribute("autocomplete")} value={el.get_attribute("value")}')
            print('  outerHTML=', el.get_attribute('outerHTML')[:400])

        buttons = driver.find_elements(By.CSS_SELECTOR, 'button')
        print('TOTAL button count', len(buttons))
        for i, el in enumerate(buttons, 1):
            visible = el.is_displayed()
            enabled = el.is_enabled()
            print(f'BUTTON {i}: visible={visible} enabled={enabled} text={repr(el.text)} aria-label={el.get_attribute("aria-label")} type={el.get_attribute("type")}')
            print('  outerHTML=', el.get_attribute('outerHTML')[:400])

    finally:
        driver.quit()
