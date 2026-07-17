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

# ── Canvas/Audio noise values — randomized once per session ───────────────────
_CANVAS_NOISE = random.uniform(-0.5, 0.5)
_AUDIO_NOISE  = random.uniform(-0.0001, 0.0001)
_HW_CONCUR    = random.choice([4, 6, 8, 12, 16])
_WEBGL_VENDOR  = random.choice([
    "Google Inc. (NVIDIA)", "Google Inc. (Intel)", "Google Inc. (AMD)",
])
_WEBGL_RENDERER = random.choice([
    "ANGLE (NVIDIA GeForce GTX 1650 Direct3D11 vs_5_0 ps_5_0)",
    "ANGLE (Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0)",
    "ANGLE (AMD Radeon RX 580 Direct3D11 vs_5_0 ps_5_0)",
])


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


def _build_stealth_script() -> str:
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
        get: () => {_HW_CONCUR}
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

    // ── Canvas fingerprint noise ({_CANVAS_NOISE:.6f}) ──────────────
    const origToDataURL = HTMLCanvasElement.prototype.toDataURL;
    HTMLCanvasElement.prototype.toDataURL = function(type) {{
        const ctx = this.getContext('2d');
        if (ctx) {{
            const imageData = ctx.getImageData(0, 0, this.width, this.height);
            for (let i = 0; i < imageData.data.length; i += 4) {{
                imageData.data[i]     = Math.min(255, imageData.data[i]     + {round(_CANVAS_NOISE)});
                imageData.data[i + 1] = Math.min(255, imageData.data[i + 1] + {round(_CANVAS_NOISE)});
            }}
            ctx.putImageData(imageData, 0, 0);
        }}
        return origToDataURL.apply(this, arguments);
    }};

    // ── WebGL vendor / renderer ──────────────────────────────────────
    const getParamOrig = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(parameter) {{
        if (parameter === 37445) return '{_WEBGL_VENDOR}';
        if (parameter === 37446) return '{_WEBGL_RENDERER}';
        return getParamOrig.call(this, parameter);
    }};
    if (typeof WebGL2RenderingContext !== 'undefined') {{
        const getParam2Orig = WebGL2RenderingContext.prototype.getParameter;
        WebGL2RenderingContext.prototype.getParameter = function(parameter) {{
            if (parameter === 37445) return '{_WEBGL_VENDOR}';
            if (parameter === 37446) return '{_WEBGL_RENDERER}';
            return getParam2Orig.call(this, parameter);
        }};
    }}

    // ── AudioContext noise ({_AUDIO_NOISE:.8f}) ──────────────────────
    const AudioContextOrig = window.AudioContext || window.webkitAudioContext;
    if (AudioContextOrig) {{
        const origCreateOscillator = AudioContextOrig.prototype.createOscillator;
        AudioContextOrig.prototype.createOscillator = function() {{
            const osc = origCreateOscillator.call(this);
            const origConnect = osc.connect.bind(osc);
            osc.connect = function(dest) {{
                const gainNode = this.context.createGain();
                gainNode.gain.value = 1 + {_AUDIO_NOISE:.8f};
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
            os.system("taskkill /F /IM chrome.exe /T >nul 2>&1")
            os.system("taskkill /F /IM undetected_chromedriver.exe /T >nul 2>&1")
            uc_exe = os.path.join(os.getenv("APPDATA", ""), "undetected_chromedriver", "undetected_chromedriver.exe")
            if os.path.exists(uc_exe):
                try:
                    os.remove(uc_exe)
                except Exception:
                    pass

        options = uc.ChromeOptions()

        # ── Persistent bot profile (sessions, cookies, localStorage) ──
        user_data_dir = r"C:\ApplyFlow\bot_chrome_profile"
        options.add_argument(f"--user-data-dir={user_data_dir}")
        options.add_argument("--profile-directory=Default")

        # ── Random User-Agent ─────────────────────────────────────────
        ua = random.choice(_USER_AGENTS)
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

        # ── Random viewport ───────────────────────────────────────────
        width, height = random_viewport_size()
        options.add_argument(f"--window-size={width},{height}")
        logger.info(f"[Browser] Viewport: {width}x{height}")

        if os.getenv("HEADLESS", "true").lower() != "false":
            options.add_argument("--headless=new")

        chrome_major = _detect_chrome_version_main()
        if chrome_major is not None:
            logger.info(f"[Browser] Detected Chrome major version {chrome_major}")
            driver = uc.Chrome(options=options, use_subprocess=True, version_main=chrome_major)
        else:
            logger.info("[Browser] Chrome version unknown; using auto-detect")
            driver = uc.Chrome(options=options, use_subprocess=True)

        # ── Inject full stealth script via CDP ────────────────────────
        stealth_js = _build_stealth_script()
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
