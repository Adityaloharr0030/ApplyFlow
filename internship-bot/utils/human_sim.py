"""
utils/human_sim.py
──────────────────
Human-realistic behavior simulation for Selenium.
Provides utilities to make bot interactions look natural:
  - human_click:  move mouse near element, brief hover, then click
  - human_type:   type with random inter-key delays
  - human_scroll: smooth scroll in increments
  - random_idle:  random pause simulating reading
"""

import logging
import random
import time

logger = logging.getLogger(__name__)


def human_click(driver, element, jitter: bool = True):
    """
    Click an element with a brief pause beforehand,
    simulating a human moving their cursor to the element.
    Uses JavaScript click as fallback if ActionChains fail.
    """
    try:
        from selenium.webdriver.common.action_chains import ActionChains

        # Small pause before clicking (human reaction time)
        time.sleep(random.uniform(0.2, 0.6))

        # Scroll element into view first
        driver.execute_script(
            "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
            element,
        )
        time.sleep(random.uniform(0.3, 0.7))

        # Move to element with slight offset for realism
        actions = ActionChains(driver)
        if jitter:
            x_offset = random.randint(-3, 3)
            y_offset = random.randint(-3, 3)
            actions.move_to_element_with_offset(element, x_offset, y_offset)
        else:
            actions.move_to_element(element)

        # Brief hover
        actions.pause(random.uniform(0.1, 0.3))
        actions.click()
        actions.perform()

    except Exception:
        # Fallback to JavaScript click
        try:
            driver.execute_script("arguments[0].click();", element)
        except Exception as e:
            logger.debug(f"[HumanSim] Click failed: {e}")
            raise


def human_type(driver, element, text: str, clear_first: bool = True):
    """
    Type text into an element with random inter-key delays,
    simulating human typing speed.
    """
    try:
        if clear_first:
            try:
                element.clear()
            except Exception:
                # If clear() fails, select all + delete
                from selenium.webdriver.common.keys import Keys
                element.send_keys(Keys.CONTROL, "a")
                time.sleep(0.1)
                element.send_keys(Keys.DELETE)
                time.sleep(0.1)

        for char in text:
            element.send_keys(char)
            # Variable typing speed: faster for common chars, slower for special chars
            if char in " \n\t":
                delay = random.uniform(0.02, 0.08)
            elif char.isupper() or char in "!@#$%^&*()":
                delay = random.uniform(0.05, 0.15)
            else:
                delay = random.uniform(0.03, 0.10)
            time.sleep(delay)

        # Brief pause after finishing typing
        time.sleep(random.uniform(0.2, 0.5))

    except Exception as e:
        # Fallback: just send_keys normally
        logger.debug(f"[HumanSim] human_type failed, using fallback: {e}")
        try:
            if clear_first:
                element.clear()
            element.send_keys(text)
        except Exception:
            pass


def human_scroll(driver, target_y: int = None, direction: str = "down"):
    """
    Smooth scroll in increments, simulating human scroll behavior.
    If target_y is provided, scrolls to that Y position.
    Otherwise scrolls a random amount in the given direction.
    """
    try:
        if target_y is not None:
            current_y = driver.execute_script("return window.pageYOffset;")
            distance = target_y - current_y
            steps = random.randint(3, 7)
            step_size = distance / steps

            for _ in range(steps):
                driver.execute_script(f"window.scrollBy(0, {int(step_size)});")
                time.sleep(random.uniform(0.05, 0.15))
        else:
            # Random scroll amount
            amount = random.randint(200, 600)
            if direction == "up":
                amount = -amount

            steps = random.randint(3, 5)
            step_size = amount / steps
            for _ in range(steps):
                driver.execute_script(f"window.scrollBy(0, {int(step_size)});")
                time.sleep(random.uniform(0.05, 0.12))

        # Brief pause after scrolling
        time.sleep(random.uniform(0.3, 0.8))

    except Exception as e:
        logger.debug(f"[HumanSim] Scroll failed: {e}")


def random_idle(min_s: float = 2.0, max_s: float = 8.0):
    """
    Random wait simulating a human reading or thinking.
    """
    duration = random.uniform(min_s, max_s)
    logger.debug(f"[HumanSim] Idle pause: {duration:.1f}s")
    time.sleep(duration)


def random_viewport_size():
    """
    Return a random realistic viewport size to avoid fingerprinting.
    """
    viewports = [
        (1366, 768),
        (1440, 900),
        (1536, 864),
        (1920, 1080),
        (1600, 900),
        (1280, 800),
        (1680, 1050),
    ]
    return random.choice(viewports)


def simulate_page_read(driver, min_s: float = 2.0, max_s: float = 5.0):
    """
    Simulate a human reading a page: scroll down a bit, pause, scroll more.
    """
    try:
        # Initial pause (reading top of page)
        time.sleep(random.uniform(min_s * 0.3, max_s * 0.3))

        # Scroll down partway
        page_height = driver.execute_script("return document.body.scrollHeight;")
        scroll_to = random.randint(int(page_height * 0.2), int(page_height * 0.5))
        human_scroll(driver, target_y=scroll_to)

        # Read pause
        time.sleep(random.uniform(min_s * 0.5, max_s * 0.5))

    except Exception as e:
        logger.debug(f"[HumanSim] Page read simulation failed: {e}")
        time.sleep(random.uniform(min_s, max_s))
