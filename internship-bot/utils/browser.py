"""
utils/browser.py
────────────────
Browser automation utilities — enhanced anti-detection.

Anti-detection layers applied:
  1. undetected_chromedriver — patches the binary to remove automation flags
  2. CDP Page.addScriptToEvaluateOnNewDocument — overrides JS properties:
       - navigator.webdriver → undefined
       - navigator.languages → ['en-IN', 'en', 'hi']
       - navigator.plugins → realistic plugin list
       - navigator.hardwareConcurrency → realistic value
       - Canvas fingerprint noise → random pixel shift per session
       - WebGL renderer/vendor → spoofed to common GPU
       - AudioContext fingerprint noise → random gain offset
       - window.chrome → inject realistic chrome runtime
  3. Randomized User-Agent (from pool of real Chrome UAs)
  4. Randomized viewport sizes
  5. Persistent bot profile (cookies + localStorage preserved across runs)
"""

import logging
import os
import re
import shutil
import subprocess
import sys
import random
import time
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Realistic Chrome User Agents (Windows, up-to-date) ────────────────────────
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.6312.86 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.69 Safari/537.36",
]

import json

def _load_or_generate_fingerprint(profile_dir: Path) -> dict:
    fp_path = profile_dir / "fingerprint.json"
    if fp_path.exists():
        try:
            with open(fp_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"[Browser] Failed to load fingerprint: {e}")
            
    # Generate new fingerprint
    from utils.human_sim import random_viewport_size
    width, height = random_viewport_size()
    fp = {
        "ua": random.choice(_USER_AGENTS),
        "canvas_noise": random.uniform(-0.5, 0.5),
        "audio_noise": random.uniform(-0.0001, 0.0001),
        "hw_concur": random.choice([4, 6, 8, 12, 16]),
        "webgl_vendor": random.choice([
            "Google Inc. (NVIDIA)", "Google Inc. (Intel)", "Google Inc. (AMD)",
        ]),
        "webgl_renderer": random.choice([
            "ANGLE (NVIDIA GeForce GTX 1650 Direct3D11 vs_5_0 ps_5_0)",
            "ANGLE (Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0)",
            "ANGLE (AMD Radeon RX 580 Direct3D11 vs_5_0 ps_5_0)",
        ]),
        "width": width,
        "height": height
    }
    
    try:
        profile_dir.mkdir(parents=True, exist_ok=True)
        with open(fp_path, "w", encoding="utf-8") as f:
            json.dump(fp, f, indent=4)
        logger.info("[Browser] Generated and saved new persistent fingerprint.")
    except Exception as e:
        logger.error(f"[Browser] Failed to save fingerprint: {e}")
        
    return fp
def _get_chrome_executable_paths() -> list[Path]:
    paths: list[Path] = []
    if sys.platform == "win32":
        chrome_path = shutil.which("chrome.exe")
        if chrome_path:
            paths.append(Path(chrome_path))
        program_files     = os.getenv("PROGRAMFILES",      r"C:\Program Files")
        program_files_x86 = os.getenv("PROGRAMFILES(X86)", r"C:\Program Files (x86)")
        paths.extend([
            Path(program_files)     / "Google" / "Chrome" / "Application" / "chrome.exe",
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
                capture_output=True, text=True, check=True,
            )
            return proc.stdout.strip()
        proc = subprocess.run(
            [str(path), "--version"], capture_output=True, text=True, check=True,
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


def _build_stealth_script(fp: dict) -> str:
    """
    Returns a JavaScript string injected into every page via CDP.
    Spoofs the most common bot-detection fingerprinting vectors:
      - navigator.webdriver
      - navigator.plugins (realistic list)
      - navigator.hardwareConcurrency
      - navigator.languages
      - window.chrome (present in real browsers)
      - Canvas toDataURL noise
      - WebGL renderer/vendor strings
      - AudioContext sample noise
    """
    return f"""
    // ── webdriver flag ───────────────────────────────────────────────
    Object.defineProperty(navigator, 'webdriver', {{
        get: () => undefined,
        configurable: true
    }});

    // ── plugins (realistic) ──────────────────────────────────────────
    const makePlugin = (name, desc, filename) => {{
        const plugin = Object.create(Plugin.prototype);
        Object.defineProperty(plugin, 'name',     {{ value: name }});
        Object.defineProperty(plugin, 'description', {{ value: desc }});
        Object.defineProperty(plugin, 'filename', {{ value: filename }});
        return plugin;
    }};
    const pluginArray = [
        makePlugin('PDF Viewer', 'Portable Document Format', 'internal-pdf-viewer'),
        makePlugin('Chrome PDF Viewer', 'Portable Document Format', 'internal-pdf-viewer'),
        makePlugin('Chromium PDF Viewer', 'Portable Document Format', 'internal-pdf-viewer'),
        makePlugin('Microsoft Edge PDF Viewer', 'Portable Document Format', 'internal-pdf-viewer'),
    ];
    Object.defineProperty(navigator, 'plugins', {{ get: () => pluginArray }});
    Object.defineProperty(navigator, 'mimeTypes', {{ get: () => [] }});

    // ── hardwareConcurrency ──────────────────────────────────────────
    Object.defineProperty(navigator, 'hardwareConcurrency', {{
        get: () => {fp["hw_concur"]}
    }});

    // ── languages ────────────────────────────────────────────────────
    Object.defineProperty(navigator, 'languages', {{
        get: () => ['en-IN', 'en', 'hi']
    }});

    // ── window.chrome (missing in headless) ──────────────────────────
    if (!window.chrome) {{
        window.chrome = {{
            app: {{ isInstalled: false, InstallState: {{}}, RunningState: {{}} }},
            runtime: {{
                id: undefined,
                connect: () => ({{}}),
                sendMessage: () => ({{}})
            }},
            loadTimes: () => ({{}}),
            csi: () => ({{}})
        }};
    }}

    // ── Canvas fingerprint noise ({fp["canvas_noise"]:.6f}) ──────────────
    const origToDataURL = HTMLCanvasElement.prototype.toDataURL;
    HTMLCanvasElement.prototype.toDataURL = function(type) {{
        const ctx = this.getContext('2d');
        if (ctx) {{
            const imageData = ctx.getImageData(0, 0, this.width, this.height);
            for (let i = 0; i < imageData.data.length; i += 4) {{
                imageData.data[i]     = Math.min(255, imageData.data[i]     + {round(fp["canvas_noise"])});
                imageData.data[i + 1] = Math.min(255, imageData.data[i + 1] + {round(fp["canvas_noise"])});
            }}
            ctx.putImageData(imageData, 0, 0);
        }}
        return origToDataURL.apply(this, arguments);
    }};

    // ── WebGL vendor / renderer ──────────────────────────────────────
    const getParamOrig = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(parameter) {{
        if (parameter === 37445) return '{fp["webgl_vendor"]}';
        if (parameter === 37446) return '{fp["webgl_renderer"]}';
        return getParamOrig.call(this, parameter);
    }};
    if (typeof WebGL2RenderingContext !== 'undefined') {{
        const getParam2Orig = WebGL2RenderingContext.prototype.getParameter;
        WebGL2RenderingContext.prototype.getParameter = function(parameter) {{
            if (parameter === 37445) return '{fp["webgl_vendor"]}';
            if (parameter === 37446) return '{fp["webgl_renderer"]}';
            return getParam2Orig.call(this, parameter);
        }};
    }}

    // ── AudioContext noise ({fp["audio_noise"]:.8f}) ──────────────────────
    const AudioContextOrig = window.AudioContext || window.webkitAudioContext;
    if (AudioContextOrig) {{
        const origCreateOscillator = AudioContextOrig.prototype.createOscillator;
        AudioContextOrig.prototype.createOscillator = function() {{
            const osc = origCreateOscillator.call(this);
            const origConnect = osc.connect.bind(osc);
            osc.connect = function(dest) {{
                const gainNode = this.context.createGain();
                gainNode.gain.value = 1 + {fp["audio_noise"]:.8f};
                origConnect(gainNode);
                gainNode.connect(dest);
                return dest;
            }};
            return osc;
        }};
    }}
    """


def create_driver():
    """
    Launch undetected_chromedriver with deep CDP-level anti-detection.
    """
    try:
        import undetected_chromedriver as uc
        from utils.human_sim import random_viewport_size

        logger.info("[Browser] Launching Chrome with dedicated bot profile...")

        if sys.platform == "win32":
            # Only kill the undetected_chromedriver executable, NOT all chrome.exe processes
            # (killing all chrome.exe would close the user's open browser windows)
            uc_exe = os.path.join(os.getenv("APPDATA", ""), "undetected_chromedriver", "undetected_chromedriver.exe")
            if os.path.exists(uc_exe):
                try:
                    os.remove(uc_exe)
                    logger.debug("[Browser] Removed stale undetected_chromedriver.exe")
                except Exception:
                    pass
            # Kill only orphaned chromedriver processes, not user Chrome
            os.system("taskkill /F /IM undetected_chromedriver.exe /T >nul 2>&1")

        options = uc.ChromeOptions()

        # ── Persistent bot profile (sessions, cookies, localStorage) ──
        # Allow overriding the profile directory via .env (e.g. for main Chrome profile)
        env_profile_path = os.getenv("CHROME_USER_DATA_DIR")
        if env_profile_path and os.path.exists(env_profile_path):
            profile_path = Path(env_profile_path)
            logger.info(f"Using custom Chrome profile from: {profile_path}")
        else:
            _project_root = Path(__file__).resolve().parents[1]
            profile_path = _project_root / "bot_chrome_profile"
            
        user_data_dir = str(profile_path)
        
        # Load or generate persistent fingerprint
        fp = _load_or_generate_fingerprint(profile_path)

        options.add_argument(f"--user-data-dir={user_data_dir}")
        options.add_argument("--profile-directory=Default")

        # ── Persistent User-Agent ─────────────────────────────────────────
        ua = fp["ua"]
        options.add_argument(f"--user-agent={ua}")
        logger.info(f"[Browser] User-Agent: {ua[:60]}...")

        # ── Standard stability flags ──────────────────────────────────
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-features=IsolateOrigins,site-per-process")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-infobars")

        # ── Persistent viewport ───────────────────────────────────────────
        width, height = fp["width"], fp["height"]
        options.add_argument(f"--window-size={width},{height}")
        logger.info(f"[Browser] Viewport: {width}x{height}")

        if os.getenv("HEADLESS", "true").lower() != "false":
            options.add_argument("--headless=new")

        chrome_major = _detect_chrome_version_main()
        if chrome_major is not None:
            logger.info(f"[Browser] Detected Chrome major version {chrome_major}")
            driver = uc.Chrome(options=options, use_subprocess=True, user_data_dir=user_data_dir, version_main=chrome_major)
        else:
            logger.info("[Browser] Chrome version unknown; using auto-detect")
            driver = uc.Chrome(options=options, use_subprocess=True, user_data_dir=user_data_dir)

        # ── Inject full stealth script via CDP ────────────────────────
        stealth_js = _build_stealth_script(fp)
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": stealth_js
        })
        logger.info("[Browser] ✓ Stealth fingerprint scripts injected (Canvas+WebGL+Audio+Plugins)")

        # ── Set implicit wait ─────────────────────────────────────────
        driver.implicitly_wait(10)
        logger.info("[Browser] ✓ Chrome launched successfully with full anti-detection")
        return driver

    except Exception as e:
        logger.error(f"[Browser] Failed to launch Chrome: {e}")
        return None
