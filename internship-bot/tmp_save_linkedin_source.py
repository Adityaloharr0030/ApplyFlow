import os
import time
from utils.browser import create_driver

os.environ['HEADLESS'] = 'false'

url = 'https://in.linkedin.com/jobs/view/software-engineer-at-mailercloud-4427920806'

if __name__ == '__main__':
    driver = create_driver()
    if not driver:
        raise SystemExit('Failed to create driver')
    try:
        driver.get(url)
        time.sleep(12)
        print('current_url=', driver.current_url)
        print('title=', driver.title)
        html = driver.page_source
        with open('tmp_linkedin_page.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print('saved tmp_linkedin_page.html', len(html), 'bytes')
    finally:
        driver.quit()
