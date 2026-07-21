"""
utils/real_mouse.py
───────────────────
Real OS-level mouse automation using PyAutoGUI.
Unlike Selenium's ActionChains (which dispatch synthetic browser events),
this module physically moves the Windows mouse cursor and generates
real click events — identical to a human using a mouse.

Websites CANNOT detect this because the events come from the OS,
not from the WebDriver protocol.
"""

import logging
import math
import random
import time
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import pyautogui
    pyautogui.FAILSAFE = False          # Don't abort if cursor hits corner
    pyautogui.PAUSE = 0.0               # We handle our own pauses
    HAS_PYAUTOGUI = True
except ImportError:
    HAS_PYAUTOGUI = False
    logger.warning("[RealMouse] pyautogui not installed — falling back to Selenium clicks")


# ─── Bézier curve helpers ──────────────────────────────────────────────────────

def _bezier_point(t: float, p0: tuple, p1: tuple, p2: tuple, p3: tuple) -> tuple:
    """Compute a point on a cubic Bézier curve at parameter t."""
    x = (
        (1 - t) ** 3 * p0[0]
        + 3 * (1 - t) ** 2 * t * p1[0]
        + 3 * (1 - t) * t ** 2 * p2[0]
        + t ** 3 * p3[0]
    )
    y = (
        (1 - t) ** 3 * p0[1]
        + 3 * (1 - t) ** 2 * t * p1[1]
        + 3 * (1 - t) * t ** 2 * p2[1]
        + t ** 3 * p3[1]
    )
    return (int(x), int(y))


def _human_curve(start: tuple, end: tuple, num_points: int = 50) -> list[tuple]:
    """
    Generate a human-like mouse path using a cubic Bézier curve
    with randomised control points.
    """
    dx = end[0] - start[0]
    dy = end[1] - start[1]

    # Control points with randomness to simulate natural hand movement
    cp1 = (
        start[0] + dx * random.uniform(0.2, 0.4) + random.randint(-40, 40),
        start[1] + dy * random.uniform(0.0, 0.3) + random.randint(-40, 40),
    )
    cp2 = (
        start[0] + dx * random.uniform(0.6, 0.8) + random.randint(-40, 40),
        start[1] + dy * random.uniform(0.7, 1.0) + random.randint(-40, 40),
    )

    return [_bezier_point(t / num_points, start, cp1, cp2, end) for t in range(num_points + 1)]


# ─── Core functions ────────────────────────────────────────────────────────────

def _get_element_screen_pos(driver, element) -> Optional[tuple]:
    """
    Get the absolute screen position (x, y) of a Selenium element.
    Accounts for browser chrome (toolbar, tabs) and scroll position.
    """
    try:
        # Get element position relative to the viewport
        rect = driver.execute_script("""
            var r = arguments[0].getBoundingClientRect();
            return {x: r.x, y: r.y, width: r.width, height: r.height};
        """, element)

        if not rect or rect['width'] == 0 or rect['height'] == 0:
            return None

        # Get browser window position on screen
        window_x = driver.execute_script("return window.screenX || window.screenLeft || 0;")
        window_y = driver.execute_script("return window.screenY || window.screenTop || 0;")

        # Chrome's outer vs inner height difference = toolbar/address bar height
        outer_height = driver.execute_script("return window.outerHeight;")
        inner_height = driver.execute_script("return window.innerHeight;")
        chrome_height = outer_height - inner_height  # Toolbar + tabs + address bar

        # Same for width (usually 0, but sidebar could add offset)
        outer_width = driver.execute_script("return window.outerWidth;")
        inner_width = driver.execute_script("return window.innerWidth;")
        chrome_width_offset = (outer_width - inner_width) // 2

        # Calculate center of element on screen
        screen_x = window_x + chrome_width_offset + rect['x'] + rect['width'] / 2
        screen_y = window_y + chrome_height + rect['y'] + rect['height'] / 2

        # Add small human-like jitter (don't click dead center every time)
        jitter_x = random.randint(-int(rect['width'] * 0.15), int(rect['width'] * 0.15))
        jitter_y = random.randint(-int(rect['height'] * 0.15), int(rect['height'] * 0.15))

        return (int(screen_x + jitter_x), int(screen_y + jitter_y))

    except Exception as e:
        logger.debug(f"[RealMouse] Failed to get element screen position: {e}")
        return None


def real_click(driver, element, double_click: bool = False):
    """
    Click an element using the REAL OS mouse pointer.
    
    1. Scrolls the element into view (Selenium)
    2. Calculates its absolute screen position
    3. Moves the mouse along a human-like Bézier curve
    4. Clicks with real OS events
    
    Falls back to Selenium ActionChains if PyAutoGUI is unavailable.
    """
    # Step 1: Scroll element into view
    try:
        driver.execute_script(
            "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
            element,
        )
        time.sleep(random.uniform(0.3, 0.6))
    except Exception:
        pass

    # Step 2: Try real mouse click via PyAutoGUI
    if HAS_PYAUTOGUI:
        target = _get_element_screen_pos(driver, element)
        if target:
            try:
                # Get current mouse position
                current_x, current_y = pyautogui.position()

                # Move along a human-like Bézier curve
                path = _human_curve((current_x, current_y), target)
                
                # Calculate movement duration based on distance
                distance = math.sqrt(
                    (target[0] - current_x) ** 2 + (target[1] - current_y) ** 2
                )
                # Faster for short distances, slower for long
                duration = min(0.8, max(0.2, distance / 2000))
                step_delay = duration / len(path)

                for point in path:
                    pyautogui.moveTo(point[0], point[1], _pause=False)
                    time.sleep(step_delay)

                # Small hover pause (human hesitation before clicking)
                time.sleep(random.uniform(0.05, 0.2))

                # Real click
                if double_click:
                    pyautogui.doubleClick()
                else:
                    pyautogui.click()

                logger.debug(f"[RealMouse] ✓ Real click at ({target[0]}, {target[1]})")
                
                # Small post-click pause
                time.sleep(random.uniform(0.1, 0.3))
                return

            except Exception as e:
                logger.debug(f"[RealMouse] PyAutoGUI click failed: {e}, trying fallback")

    # Step 3: Fallback to Selenium ActionChains
    try:
        from selenium.webdriver.common.action_chains import ActionChains

        time.sleep(random.uniform(0.2, 0.5))
        actions = ActionChains(driver)
        x_off = random.randint(-3, 3)
        y_off = random.randint(-3, 3)
        actions.move_to_element_with_offset(element, x_off, y_off)
        actions.pause(random.uniform(0.1, 0.3))
        actions.click()
        actions.perform()
        logger.debug("[RealMouse] Used Selenium ActionChains fallback")
    except Exception:
        # Last resort: JavaScript click
        try:
            driver.execute_script("arguments[0].click();", element)
            logger.debug("[RealMouse] Used JavaScript click fallback")
        except Exception as e:
            logger.error(f"[RealMouse] All click methods failed: {e}")
            raise


def real_type(driver, element, text: str, clear_first: bool = True):
    """
    Type text using real keyboard events via PyAutoGUI.
    First clicks the element with real_click, then types character by character.
    """
    # Focus the element with a real click
    real_click(driver, element)
    time.sleep(random.uniform(0.1, 0.3))

    if clear_first:
        # Select all + delete using real keyboard
        if HAS_PYAUTOGUI:
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(random.uniform(0.05, 0.15))
            pyautogui.press('delete')
            time.sleep(random.uniform(0.05, 0.15))
        else:
            try:
                element.clear()
            except Exception:
                from selenium.webdriver.common.keys import Keys
                element.send_keys(Keys.CONTROL, "a")
                time.sleep(0.1)
                element.send_keys(Keys.DELETE)

    if HAS_PYAUTOGUI:
        # Type character by character with human-like delays
        for char in text:
            try:
                pyautogui.write(char, interval=0)
            except Exception:
                # For special characters, use pyperclip + paste
                try:
                    import pyperclip
                    pyperclip.copy(char)
                    pyautogui.hotkey('ctrl', 'v')
                except Exception:
                    element.send_keys(char)

            # Human-like typing speed
            if char in " \n\t":
                delay = random.uniform(0.02, 0.08)
            elif char.isupper() or char in "!@#$%^&*()":
                delay = random.uniform(0.05, 0.15)
            else:
                delay = random.uniform(0.03, 0.10)
            time.sleep(delay)
    else:
        # Fallback to Selenium send_keys
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(0.03, 0.10))

    # Brief pause after typing
    time.sleep(random.uniform(0.2, 0.5))


def real_scroll(driver, direction: str = "down", amount: int = None):
    """
    Scroll using real mouse wheel events.
    """
    if amount is None:
        amount = random.randint(3, 8)

    if HAS_PYAUTOGUI:
        clicks = amount if direction == "up" else -amount
        # Scroll in small increments
        steps = random.randint(2, 4)
        per_step = clicks // steps
        remainder = clicks - (per_step * steps)
        
        for i in range(steps):
            scroll_amount = per_step + (remainder if i == steps - 1 else 0)
            pyautogui.scroll(scroll_amount)
            time.sleep(random.uniform(0.05, 0.15))
        
        time.sleep(random.uniform(0.2, 0.5))
    else:
        # Fallback to JavaScript scroll
        pixels = amount * 100
        if direction == "up":
            pixels = -pixels
        driver.execute_script(f"window.scrollBy(0, {pixels});")
        time.sleep(random.uniform(0.3, 0.8))


def bring_browser_to_front(driver):
    """
    Bring the browser window to the foreground so real mouse clicks
    land on the correct window.

    Uses Win32 API (win32gui) for true OS-level foreground promotion on Windows.
    Falls back to JavaScript focus on Linux/macOS.
    """
    # Step 1: Switch Selenium focus to the current window handle
    try:
        driver.switch_to.window(driver.current_window_handle)
    except Exception:
        pass

    # Step 2: Try Win32 API for true OS-level foreground (Windows only)
    try:
        import win32gui
        import win32con

        title = driver.title or ""

        def _enum_callback(hwnd, results):
            if win32gui.IsWindowVisible(hwnd):
                win_title = win32gui.GetWindowText(hwnd)
                # Match Chrome windows (title contains page title or "Chrome")
                if title and title[:20].lower() in win_title.lower():
                    results.append(hwnd)
                elif "chrome" in win_title.lower() or "chromium" in win_title.lower():
                    results.append(hwnd)

        matches = []
        win32gui.EnumWindows(_enum_callback, matches)

        if matches:
            hwnd = matches[0]
            # Restore if minimised, then bring to foreground
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
            logger.debug(f"[RealMouse] ✓ Win32 foreground focus set (hwnd={hwnd})")
            return
    except ImportError:
        pass  # pywin32 not installed — fall through to JS focus
    except Exception as e:
        logger.debug(f"[RealMouse] Win32 focus failed: {e}")

    # Step 3: JavaScript focus as universal fallback
    try:
        driver.execute_script("window.focus();")
    except Exception:
        pass
