"""
utils/browser.py
────────────────
Browser automation utilities.
"""

import logging
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

logger = logging.getLogger(__name__)


def _get_chrome_executable_paths() -> list[Path]:
    paths: list[Path] = []

    if sys.platform == "win32":
        chrome_path = shutil.which("chrome.exe")
        if chrome_path:
            paths.append(Path(chrome_path))

        program_files = os.getenv("PROGRAMFILES", r"C:\Program Files")
        program_files_x86 = os.getenv("PROGRAMFILES(X86)", r"C:\Program Files (x86)")

        paths.extend([
            Path(program_files) / "Google" / "Chrome" / "Application" / "chrome.exe",
            Path(program_files_x86) / "Google" / "Chrome" / "Application" / "chrome.exe",
        ])
    else:
        chrome_path = shutil.which("google-chrome") or shutil.which("chrome") or shutil.which("chromium-browser")
        if chrome_path:
            paths.append(Path(chrome_path))

    return [p for p in paths if p.exists()]


def _read_version_from_executable(path: Path) -> str | None:
    try:
        if sys.platform == "win32":
            proc = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 f"(Get-Item '{path}').VersionInfo.ProductVersion"],
                capture_output=True,
                text=True,
                check=True,
            )
            return proc.stdout.strip()

        proc = subprocess.run(
            [str(path), "--version"],
            capture_output=True,
            text=True,
            check=True,
        )
        return proc.stdout.strip()
    except Exception:
        return None


def _detect_chrome_version_main() -> int | None:
    for path in _get_chrome_executable_paths():
        version_text = _read_version_from_executable(path)
        if not version_text:
            continue

        match = re.search(r"(\d+)\.", version_text)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                continue

    return None


def create_driver():
    """
    Launch undetected_chromedriver using a dedicated bot profile.
    Enhanced with anti-detection measures:
    - Random viewport sizes
    - Disabled automation flags
    - User-agent rotation
    - navigator.webdriver override
    """
    try:
        import undetected_chromedriver as uc
        from utils.human_sim import random_viewport_size

        logger.info("[Browser] Launching Chrome with dedicated bot profile...")

        if sys.platform == "win32":
            # Force kill any stuck/orphaned chrome processes before launching to prevent freezing
            os.system("taskkill /F /IM chrome.exe /T >nul 2>&1")
            os.system("taskkill /F /IM undetected_chromedriver.exe /T >nul 2>&1")

            # Fix WinError 183 by removing the old executable if it exists
            uc_exe = os.path.join(os.getenv("APPDATA", ""), "undetected_chromedriver", "undetected_chromedriver.exe")
            if os.path.exists(uc_exe):
                try:
                    os.remove(uc_exe)
                except Exception:
                    pass

        options = uc.ChromeOptions()
        user_data_dir = r"C:\ApplyFlow\bot_chrome_profile"
        options.add_argument(f"--user-data-dir={user_data_dir}")
        options.add_argument("--profile-directory=Default")

        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        # ── Anti-detection: Random viewport size ───────────────────────────
        width, height = random_viewport_size()
        options.add_argument(f"--window-size={width},{height}")
        logger.info(f"[Browser] Viewport: {width}x{height}")

        # ── Anti-detection: Additional stealth flags ──────────────────────
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-features=IsolateOrigins,site-per-process")
        options.add_argument("--disable-popup-blocking")

        # (excludeSwitches is handled natively by undetected_chromedriver)

        if os.getenv("HEADLESS", "true").lower() != "false":
            options.add_argument("--headless=new")

        chrome_major = _detect_chrome_version_main()
        if chrome_major is not None:
            logger.info(f"[Browser] Detected Chrome major version {chrome_major}")
            driver = uc.Chrome(options=options, use_subprocess=True, version_main=chrome_major)
        else:
            logger.info("[Browser] Could not detect local Chrome version; using undetected_chromedriver auto-detect")
            driver = uc.Chrome(options=options, use_subprocess=True)

        # ── Anti-detection: Override navigator.webdriver ───────────────────
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                Object.defineProperty(navigator, 'languages', { get: () => ['en-IN', 'en', 'hi'] });
                Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            """
        })

        driver.implicitly_wait(10)
        logger.info("[Browser] ✓ Chrome launched successfully with anti-detection")
        return driver
    except Exception as e:
        logger.error(f"[Browser] Failed to launch Chrome: {e}")
        return None

