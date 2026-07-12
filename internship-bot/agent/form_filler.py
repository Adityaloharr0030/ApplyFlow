"""
agent/form_filler.py
────────────────────
Smart form field detection and filling for job application forms.

Handles:
  - India-specific fields (Notice Period, CTC, Relocate, etc.)
  - Generic screening questions via AI
  - Q&A answer caching for consistency
  - Text inputs, textareas, dropdowns, radio buttons, checkboxes
"""

import json
import logging
import os
import re
import time
import random

logger = logging.getLogger(__name__)

from agent.ai_client import get_ai_response
from agent.qa_cache import get_cached_answer, cache_answer

# ── India-Specific Known Fields ────────────────────────────────────────────────
# Maps question label keywords → a function that extracts the answer from profile.

INDIA_FIELDS = {
    # Notice period
    "notice period": lambda p: p.get("notice_period", "Immediate"),
    "notice": lambda p: p.get("notice_period", "Immediate"),
    # CTC
    "current ctc": lambda p: p.get("current_ctc", "0"),
    "current salary": lambda p: p.get("current_ctc", "0"),
    "present ctc": lambda p: p.get("current_ctc", "0"),
    "expected ctc": lambda p: p.get("expected_ctc", "As per industry standards"),
    "expected salary": lambda p: p.get("expected_ctc", "As per industry standards"),
    "salary expectation": lambda p: p.get("expected_ctc", "As per industry standards"),
    # Relocation
    "willing to relocate": lambda p: p.get("willing_to_relocate", "Yes"),
    "relocate": lambda p: p.get("willing_to_relocate", "Yes"),
    "relocation": lambda p: p.get("willing_to_relocate", "Yes"),
    # Work mode
    "work from home": lambda p: "Yes" if "remote" in str(p.get("preferred_mode", [])).lower() else "No",
    "remote work": lambda p: "Yes" if "remote" in str(p.get("preferred_mode", [])).lower() else "No",
    "hybrid": lambda p: p.get("open_to_hybrid", "Yes"),
    "open to hybrid": lambda p: p.get("open_to_hybrid", "Yes"),
    "work mode": lambda p: p.get("preferred_mode", ["remote"])[0] if isinstance(p.get("preferred_mode"), list) else p.get("preferred_mode", "remote"),
    # Experience
    "years of experience": lambda p: p.get("years_of_experience", "0"),
    "total experience": lambda p: p.get("years_of_experience", "0"),
    "experience in years": lambda p: p.get("years_of_experience", "0"),
    "relevant experience": lambda p: p.get("years_of_experience", "0"),
    # Qualification
    "highest qualification": lambda p: p.get("degree", "B.Tech"),
    "education": lambda p: p.get("degree", "B.Tech"),
    "qualification": lambda p: p.get("degree", "B.Tech"),
    # Availability
    "available to join": lambda p: "Yes" if p.get("notice_period", "Immediate") == "Immediate" else f"After {p.get('notice_period')} notice period",
    "join immediately": lambda p: "Yes" if p.get("notice_period", "Immediate") == "Immediate" else "No",
    "start date": lambda p: "Immediately" if p.get("notice_period", "Immediate") == "Immediate" else f"After {p.get('notice_period')}",
    "available": lambda p: "Yes, I am available to start immediately.",
    # Personal
    "gender": lambda p: p.get("gender", ""),
    "date of birth": lambda p: p.get("dob", ""),
    "phone": lambda p: p.get("phone", ""),
    "mobile": lambda p: p.get("phone", ""),
    "city": lambda p: p.get("location", "").split(",")[0].strip() if p.get("location") else "",
    "current location": lambda p: p.get("location", ""),
    "current city": lambda p: p.get("location", "").split(",")[0].strip() if p.get("location") else "",
    # Work authorization
    "work authorization": lambda p: p.get("work_authorization", "Indian Citizen"),
    "authorized to work": lambda p: "Yes",
    "visa": lambda p: p.get("work_authorization", "No visa required (Indian Citizen)"),
    # LinkedIn
    "linkedin": lambda p: p.get("linkedin", ""),
    "linkedin profile": lambda p: p.get("linkedin", ""),
    "linkedin url": lambda p: p.get("linkedin", ""),
    # GitHub / Portfolio
    "github": lambda p: p.get("github", ""),
    "portfolio": lambda p: p.get("github", ""),
    "website": lambda p: p.get("github", ""),
}


def _match_india_field(label: str, profile: dict) -> str | None:
    """
    Check if a form label matches any known India-specific field.
    Returns the answer string or None.
    """
    label_lower = label.lower().strip()

    # Try direct keyword match (longest match first for specificity)
    sorted_keys = sorted(INDIA_FIELDS.keys(), key=len, reverse=True)
    for keyword in sorted_keys:
        if keyword in label_lower:
            answer = INDIA_FIELDS[keyword](profile)
            if answer:
                return str(answer)

    return None


def answer_question(question: str, profile: dict) -> str:
    """
    Generate a smart, contextual answer to an application form question.

    Priority:
    1. India-specific field match (instant, no API call)
    2. Q&A cache hit (fuzzy match, no API call)
    3. AI-generated answer (Gemini/Claude)
    4. Fallback generic answer
    """
    if not question or len(question.strip()) < 3:
        return "Yes, I am available and meet the requirements."

    # 1. Check India-specific fields
    india_answer = _match_india_field(question, profile)
    if india_answer:
        logger.info(f"  [FormFiller] India field match: {question[:40]}... → {india_answer[:30]}")
        return india_answer

    # 2. Check Q&A cache
    cached = get_cached_answer(question)
    if cached:
        logger.info(f"  [FormFiller] Cache hit: {question[:40]}...")
        return cached

    # 3. AI-generated answer
    try:
        system_prompt = "You are answering a specific question on a job application form on behalf of the candidate."
        user_prompt = f"""Keep the answer extremely concise, professional, and directly address the question (1-3 sentences max). Do not write a full cover letter.

CANDIDATE INFO:
Name: {profile.get('name', '')}
Degree: {profile.get('degree', '')} ({profile.get('year', '')})
College: {profile.get('college', '')}
Skills: {', '.join(profile.get('skills', []))}
Experience/Projects: {json.dumps(profile.get('projects', []))}
Notice Period: {profile.get('notice_period', 'Immediate')}
Expected CTC: {profile.get('expected_ctc', 'As per industry standards')}
Location: {profile.get('location', '')}

QUESTION: "{question}"

Write ONLY the answer to the question."""

        answer = get_ai_response(system_prompt, user_prompt, max_tokens=512, response_format="text")

        if answer:
            answer = answer.strip()
            # Cache for future reuse
            cache_answer(question, answer)
            logger.info(f"  [FormFiller] AI answer generated: {question[:40]}...")
            return answer

    except Exception as e:
        logger.error(f"  [FormFiller] AI answer generation failed: {e}")

    # 4. Fallback
    return "Yes, I am available to start immediately and meet the requirements."


def fill_form_fields(driver, profile: dict, skip_selectors: list = None) -> int:
    """
    Scan visible form fields on the page and fill them intelligently.

    Handles:
    - Text inputs with associated labels
    - Textareas
    - Dropdowns (select elements)
    - Radio buttons
    - Checkboxes (for boolean questions like "willing to relocate")

    Args:
        driver:          Selenium WebDriver
        profile:         User's profile dict
        skip_selectors:  CSS selectors of fields to skip (e.g., already-filled cover letter)

    Returns:
        Number of fields filled.
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import Select

    skip_selectors = skip_selectors or []
    filled = 0

    # ── Text inputs and textareas ──────────────────────────────────────────
    try:
        inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='text'], input[type='number'], input[type='tel'], input[type='email'], input[type='url'], textarea")

        for inp in inputs:
            try:
                if not inp.is_displayed() or not inp.is_enabled():
                    continue

                # Skip if already filled
                current_value = inp.get_attribute("value") or inp.text
                if current_value and current_value.strip():
                    continue

                # Skip specified selectors
                should_skip = False
                for skip_sel in skip_selectors:
                    try:
                        skip_els = driver.find_elements(By.CSS_SELECTOR, skip_sel)
                        if inp in skip_els:
                            should_skip = True
                            break
                    except Exception:
                        pass
                if should_skip:
                    continue

                # Find associated label
                label_text = _get_field_label(driver, inp)
                if not label_text or len(label_text) < 3:
                    continue

                # Get answer
                answer = answer_question(label_text, profile)
                if answer:
                    try:
                        inp.clear()
                    except Exception:
                        pass
                    inp.send_keys(answer)
                    filled += 1
                    logger.info(f"  [FormFiller] Filled: {label_text[:30]}... → {answer[:30]}...")
                    time.sleep(random.uniform(0.3, 0.8))

            except Exception as e:
                logger.debug(f"  [FormFiller] Error filling input: {e}")
                continue

    except Exception as e:
        logger.debug(f"  [FormFiller] Error scanning inputs: {e}")

    # ── Dropdowns (select elements) ────────────────────────────────────────
    try:
        selects = driver.find_elements(By.TAG_NAME, "select")
        for sel_el in selects:
            try:
                if not sel_el.is_displayed() or not sel_el.is_enabled():
                    continue

                label_text = _get_field_label(driver, sel_el)
                if not label_text:
                    continue

                answer = answer_question(label_text, profile)
                if not answer:
                    continue

                select = Select(sel_el)
                options = select.options

                # Try to match answer to an option
                best_option = _find_best_option(options, answer)
                if best_option:
                    select.select_by_visible_text(best_option.text)
                    filled += 1
                    logger.info(f"  [FormFiller] Selected: {label_text[:30]}... → {best_option.text}")
                    time.sleep(random.uniform(0.3, 0.6))

            except Exception as e:
                logger.debug(f"  [FormFiller] Error filling select: {e}")
                continue

    except Exception as e:
        logger.debug(f"  [FormFiller] Error scanning selects: {e}")

    # ── Radio buttons ─────────────────────────────────────────────────────
    try:
        # Find radio button groups
        radio_groups = {}
        radios = driver.find_elements(By.CSS_SELECTOR, "input[type='radio']")
        for radio in radios:
            name = radio.get_attribute("name")
            if name:
                if name not in radio_groups:
                    radio_groups[name] = []
                radio_groups[name].append(radio)

        for group_name, group_radios in radio_groups.items():
            try:
                # Check if any is already selected
                if any(r.is_selected() for r in group_radios):
                    continue

                # Find the question/label for this group
                label_text = _get_field_label(driver, group_radios[0])
                if not label_text:
                    continue

                answer = answer_question(label_text, profile)
                if not answer:
                    continue

                # Match answer to radio option
                answer_lower = answer.lower().strip()
                for radio in group_radios:
                    radio_label = _get_radio_label(driver, radio)
                    if radio_label and (
                        radio_label.lower().strip() == answer_lower
                        or answer_lower in radio_label.lower()
                        or radio_label.lower() in answer_lower
                    ):
                        if radio.is_displayed():
                            try:
                                radio.click()
                            except Exception:
                                driver.execute_script("arguments[0].click();", radio)
                            filled += 1
                            logger.info(f"  [FormFiller] Radio: {label_text[:30]}... → {radio_label}")
                            time.sleep(random.uniform(0.2, 0.5))
                            break

            except Exception as e:
                logger.debug(f"  [FormFiller] Error filling radio group: {e}")
                continue

    except Exception as e:
        logger.debug(f"  [FormFiller] Error scanning radios: {e}")

    logger.info(f"  [FormFiller] Filled {filled} form field(s)")
    return filled


def _get_field_label(driver, element) -> str:
    """
    Find the label/question text associated with a form field.
    Tries multiple strategies.
    """
    from selenium.webdriver.common.by import By

    # Strategy 1: Associated <label> via 'for' attribute
    try:
        el_id = element.get_attribute("id")
        if el_id:
            labels = driver.find_elements(By.CSS_SELECTOR, f"label[for='{el_id}']")
            for label in labels:
                text = label.text.strip()
                if text and len(text) > 2:
                    return text
    except Exception:
        pass

    # Strategy 2: Parent/ancestor label
    try:
        label = element.find_element(By.XPATH, "ancestor::label[1]")
        text = label.text.strip()
        if text and len(text) > 2:
            return text
    except Exception:
        pass

    # Strategy 3: Preceding sibling label
    try:
        label = element.find_element(By.XPATH, "preceding-sibling::label[1]")
        text = label.text.strip()
        if text and len(text) > 2:
            return text
    except Exception:
        pass

    # Strategy 4: Parent's preceding label or div with question class
    try:
        label = element.find_element(
            By.XPATH,
            "./preceding::label[1] | "
            "./preceding::div[contains(@class, 'question')][1] | "
            "./preceding::span[contains(@class, 'label')][1] | "
            "./preceding::p[contains(@class, 'question')][1]"
        )
        text = label.text.strip()
        if text and len(text) > 2:
            return text
    except Exception:
        pass

    # Strategy 5: Placeholder attribute
    try:
        placeholder = element.get_attribute("placeholder")
        if placeholder and len(placeholder) > 2:
            return placeholder
    except Exception:
        pass

    # Strategy 6: aria-label
    try:
        aria = element.get_attribute("aria-label")
        if aria and len(aria) > 2:
            return aria
    except Exception:
        pass

    # Strategy 7: title attribute
    try:
        title = element.get_attribute("title")
        if title and len(title) > 2:
            return title
    except Exception:
        pass

    return ""


def _get_radio_label(driver, radio_element) -> str:
    """Get the label text for a radio button."""
    from selenium.webdriver.common.by import By

    # Check for associated label
    try:
        el_id = radio_element.get_attribute("id")
        if el_id:
            labels = driver.find_elements(By.CSS_SELECTOR, f"label[for='{el_id}']")
            for label in labels:
                text = label.text.strip()
                if text:
                    return text
    except Exception:
        pass

    # Check parent label
    try:
        label = radio_element.find_element(By.XPATH, "ancestor::label[1]")
        text = label.text.strip()
        if text:
            return text
    except Exception:
        pass

    # Check next sibling text
    try:
        sibling = radio_element.find_element(By.XPATH, "following-sibling::*[1]")
        text = sibling.text.strip()
        if text:
            return text
    except Exception:
        pass

    # Value attribute as last resort
    try:
        value = radio_element.get_attribute("value")
        if value:
            return value
    except Exception:
        pass

    return ""


def _find_best_option(options, answer: str):
    """
    Find the best matching option in a dropdown for the given answer.
    """
    answer_lower = answer.lower().strip()

    # Remove "Select" / "Choose" / placeholder options
    real_options = [o for o in options if o.text.strip().lower() not in (
        "", "select", "choose", "-- select --", "select one", "please select", "select..."
    )]

    if not real_options:
        return None

    # Exact match
    for opt in real_options:
        if opt.text.strip().lower() == answer_lower:
            return opt

    # Contains match
    for opt in real_options:
        opt_text = opt.text.strip().lower()
        if answer_lower in opt_text or opt_text in answer_lower:
            return opt

    # For yes/no questions, match "yes"/"no" answers
    if answer_lower in ("yes", "true", "1"):
        for opt in real_options:
            if opt.text.strip().lower() in ("yes", "true", "1"):
                return opt

    if answer_lower in ("no", "false", "0"):
        for opt in real_options:
            if opt.text.strip().lower() in ("no", "false", "0"):
                return opt

    # Numeric matching (for CTC/experience in ranges)
    try:
        answer_num = float(re.sub(r'[^\d.]', '', answer_lower) or 0)
        for opt in real_options:
            opt_text = opt.text.strip().lower()
            # Match ranges like "0-2 years", "3-5 LPA"
            range_match = re.search(r'(\d+)\s*[-–to]+\s*(\d+)', opt_text)
            if range_match:
                low, high = float(range_match.group(1)), float(range_match.group(2))
                if low <= answer_num <= high:
                    return opt
    except Exception:
        pass

    # If nothing matched, pick first real option (better than leaving blank)
    return real_options[0] if real_options else None
