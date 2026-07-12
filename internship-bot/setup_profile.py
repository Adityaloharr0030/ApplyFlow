import os
import time

print("============================================================")
print("ApplyFlow - Dedicated Chrome Profile Setup")
print("============================================================")
print("\nLaunching a fresh Chrome window for the bot...")
print("1. Log into your accounts (Internshala, LinkedIn, etc.)")
print("2. Make sure you click 'Remember me' if asked")
print("3. Once you are fully logged in, CLOSE the Chrome window.")
print("\nStarting Chrome in 3 seconds...")
time.sleep(3)

# Temporarily disable HEADLESS for setup
os.environ["HEADLESS"] = "false"

from utils.browser import create_driver

driver = create_driver()
if driver is None:
    print("\nFailed to launch Chrome.")
else:
    print("\nChrome launched! Please log in to your platforms now.")
    print("Waiting for you to close the browser window...")
    
    # Wait until the user closes the window
    while True:
        try:
            # Check if window is still open
            _ = driver.current_url
            time.sleep(2)
        except Exception:
            # Exception means the user closed the window or driver quit
            print("\nBrowser closed. Dedicated profile is now ready to use!")
            break

