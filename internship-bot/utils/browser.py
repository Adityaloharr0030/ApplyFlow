"""
utils/browser.py
────────────────
Browser automation utilities.
"""

import logging
import os
import time

logger = logging.getLogger(__name__)

def create_driver():
    """
    Launch undetected_chromedriver.
    """
    try:
        import undetected_chromedriver as uc
        
        logger.info("[Browser] Launching Chrome with user profile...")
        # Removed taskkill as it terminates the user's active browser!
        
        options = uc.ChromeOptions()
        user_data_dir = r"C:\ApplyFlow\bot_chrome_profile"
        options.add_argument(f"--user-data-dir={user_data_dir}")
        options.add_argument("--profile-directory=Default")
            
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        
        if os.getenv("HEADLESS", "true").lower() != "false":
            options.add_argument("--headless=new")
            
        logger.info("[Browser] Launching Chrome...")
        driver = uc.Chrome(options=options, use_subprocess=True, version_main=149)
        driver.implicitly_wait(10)
        return driver
    except Exception as e:
        logger.error(f"[Browser] Failed to launch Chrome: {e}")
        return None
