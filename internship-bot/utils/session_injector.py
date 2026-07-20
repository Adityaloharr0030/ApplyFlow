import os
import json
import logging
import time
import sys
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

SESSION_DIR = Path(__file__).resolve().parents[1] / "data" / "sessions"

def load_session_into_driver(driver, platform: str) -> bool:
    """
    Attempts to load a captured session (cookies + localStorage) for the given platform.
    Returns True if the session was successfully injected.
    """
    session_file = SESSION_DIR / f"{platform}_session.json"
    
    if not session_file.exists():
        logger.debug(f"[Session] No captured session found for {platform}.")
        return False
        
    try:
        with open(session_file, "r", encoding="utf-8") as f:
            at_rest_data = json.load(f)
            
        # Check staleness (7 days)
        if "capturedAt" in at_rest_data:
            captured_dt = datetime.fromisoformat(at_rest_data["capturedAt"].replace("Z", "+00:00"))
            age = (datetime.now().astimezone() - captured_dt).days
            if age > 7:
                logger.warning(f"[Session] Captured session for {platform} is stale (>7 days old). Ignoring.")
                return False
                
        # Decrypt payload
        # Ensure we can import the key securely
        sys.path.append(str(Path(__file__).resolve().parents[1]))
        try:
            from dashboard import get_aesgcm_key
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            
            key = get_aesgcm_key()
            aesgcm = AESGCM(key)
            ciphertext = bytes(at_rest_data["encrypted_blob"])
            iv = bytes(at_rest_data["iv"])
            plaintext = aesgcm.decrypt(iv, ciphertext, None)
            session_data = json.loads(plaintext.decode('utf-8'))
        except Exception as e:
            logger.error(f"[Session] Failed to decrypt session payload for {platform}: {e}")
            return False
                
        domain = session_data.get("domain", "")
        if not domain:
            return False
            
        # 1. Navigate to the base domain (cookies require being on the domain)
        url = f"https://www.{domain.lstrip('.')}" if not domain.startswith("http") else domain
        # Adjust URL for some platforms
        if platform == "internshala":
            url = "https://internshala.com"
        elif platform == "unstop":
            url = "https://unstop.com"
            
        driver.get(url)
        time.sleep(2) # Wait for initial load
        
        # 2. Clear existing cookies
        driver.delete_all_cookies()
        
        # 3. Inject cookies
        cookies_added = 0
        for cookie in session_data.get("cookies", []):
            try:
                # Selenium requires specific keys, remove others
                c = {
                    "name": cookie["name"],
                    "value": cookie["value"],
                    "domain": cookie["domain"],
                    "path": cookie["path"],
                    "secure": cookie["secure"],
                }
                # Optional keys
                if "httpOnly" in cookie: c["httpOnly"] = cookie["httpOnly"]
                if "sameSite" in cookie: c["sameSite"] = cookie["sameSite"]
                if "expirationDate" in cookie: c["expiry"] = int(cookie["expirationDate"])
                
                driver.add_cookie(c)
                cookies_added += 1
            except Exception as e:
                logger.debug(f"[Session] Failed to add cookie {cookie.get('name')}: {e}")
                
        # 4. Inject localStorage
        ls_data = session_data.get("localStorage", {})
        if ls_data:
            script = ""
            for k, v in ls_data.items():
                # Escape for JS string
                safe_k = json.dumps(k)
                safe_v = json.dumps(v)
                script += f"window.localStorage.setItem({safe_k}, {safe_v});\n"
            try:
                driver.execute_script(script)
            except Exception as e:
                logger.debug(f"[Session] Failed to inject localStorage: {e}")
                
        logger.info(f"[Session] Injected {cookies_added} cookies and {len(ls_data)} localStorage items for {platform}.")
        
        # 5. Refresh to apply session
        driver.refresh()
        time.sleep(3)
        
        return True
        
    except Exception as e:
        logger.error(f"[Session] Error loading session for {platform}: {e}")
        return False
