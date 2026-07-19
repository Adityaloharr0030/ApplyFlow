import os
import json
import time
import requests
import threading
import subprocess
from datetime import datetime
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

STATIC_KEY = b"applyflow_mvp_secret_key_1234567"
STATIC_SALT = b"applyflow_salt"

def get_aesgcm_key():
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=STATIC_SALT,
        iterations=100000,
    )
    return kdf.derive(STATIC_KEY)

def encrypt_data(data_str: str):
    key = get_aesgcm_key()
    aesgcm = AESGCM(key)
    iv = os.urandom(12)
    ciphertext = aesgcm.encrypt(iv, data_str.encode("utf-8"), None)
    return list(ciphertext), list(iv)

def run_backend():
    print("[Test] Starting dashboard backend...")
    # Run uvicorn programmatically
    import uvicorn
    import dashboard
    uvicorn.run(dashboard.app, host="127.0.0.1", port=8000, log_level="error")

if __name__ == "__main__":
    # 1. Start backend in background thread
    server_thread = threading.Thread(target=run_backend, daemon=True)
    server_thread.start()
    time.sleep(3) # Wait for server to start

    # 2. Create mock session data
    mock_session = {
        "domain": "linkedin.com",
        "capturedAt": datetime.utcnow().isoformat() + "Z",
        "cookies": [
            {
                "name": "li_at",
                "value": "AQED_TEST_COOKIE_VALUE",
                "domain": ".linkedin.com",
                "path": "/",
                "secure": True,
                "httpOnly": True,
                "sameSite": "None",
                "expirationDate": time.time() + 86400
            }
        ],
        "localStorage": {
            "test_key": "test_value"
        }
    }

    # 3. Encrypt payload
    print("[Test] Encrypting mock session data...")
    ciphertext, iv = encrypt_data(json.dumps(mock_session))

    # 4. Send POST request
    print("[Test] Uploading session to backend via API...")
    payload = {
        "platform": "linkedin",
        "encrypted_blob": ciphertext,
        "iv": iv
    }
    try:
        res = requests.post("http://127.0.0.1:8000/api/session/upload", json=payload)
        print(f"[Test] Upload Response: {res.status_code} - {res.text}")
    except Exception as e:
        print(f"[Test] Failed to upload: {e}")
        exit(1)

    # 5. Test session injector
    print("[Test] Testing Session Injector...")
    from utils.session_injector import load_session_into_driver
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options

    options = Options()
    options.add_argument("--headless=new")
    driver = webdriver.Chrome(options=options)
    
    try:
        success = load_session_into_driver(driver, "linkedin")
        print(f"[Test] load_session_into_driver returned: {success}")
        
        # Verify cookies
        driver.get("https://www.linkedin.com")
        cookies = driver.get_cookies()
        print(f"[Test] Cookies currently in browser: {len(cookies)}")
        for c in cookies:
            if c["name"] == "li_at":
                print(f"      -> Found our injected cookie! value={c['value']}")
    finally:
        driver.quit()
        print("[Test] Done.")
