import os
import sys
import time

# Force live mode (disable DRY_RUN)
os.environ["DRY_RUN"] = "false"
os.environ["HEADLESS"] = "false"

from utils.browser import create_driver
from platforms.unstop import UnstopPlatform
from platforms.login import login_unstop

def run_quick_test():
    print("==================================================")
    print(" QUICK APPLY TEST (Unstop)")
    print("==================================================")
    print("Starting Chrome...")
    
    driver = create_driver()
    if not driver:
        print("Failed to start Chrome.")
        sys.exit(1)

    try:
        print("\n1. Ensuring you are logged in...")
        if not login_unstop(driver):
            print("❌ Login failed. Please run setup_profile.py first.")
            return

        print("\n2. Navigating to an Unstop listing...")
        
        # Go directly to an unstop internship URL
        test_url = "https://unstop.com/internships/software-development-engineer-intern-amazon-1087455"
        driver.get(test_url)
        time.sleep(3)
        
        print("\n3. Attempting to apply...")
        platform = UnstopPlatform()
        result = platform.apply(
            listing={"title": "SDE Intern", "company": "Amazon", "apply_url": test_url},
            cover_note="Hi, I am very interested in this role. Thank you!",
            profile={"keywords": ["frontend"]},
            driver=driver
        )
        
        if not result["success"]:
            print("Apply failed. Saving screenshot to unstop_screenshot.png...")
            driver.save_screenshot("unstop_screenshot.png")
            with open("unstop_page.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
                
        print("\n==================================================")
        print(f"RESULT: {result}")
        print("==================================================")
        
        print("\nWaiting 15 seconds so you can see what happened...")
        time.sleep(15)
        
    finally:
        driver.quit()

if __name__ == "__main__":
    run_quick_test()
