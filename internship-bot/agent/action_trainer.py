"""
agent/action_trainer.py
────────────────────────
Auto-training recorder for ApplyFlow.

Every action the bot takes — form fills, Q&A answers, scoring decisions,
button clicks — is recorded to JSONL files that grow with every run.

This builds a live training dataset that can be used to:
  - Fine-tune AI models on real application data
  - Analyse which Q&A answers work best
  - Track scoring accuracy over time
  - Review bot behaviour for any application

Training data lives in: data/training/
  ├── qa_pairs.jsonl      — every form question + answer filled
  ├── score_pairs.jsonl   — every listing scored + apply/skip decision
  └── actions.jsonl       — every button click, page visit, step taken
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

TRAINING_DIR = Path("./data/training")


def _ensure_dir():
    TRAINING_DIR.mkdir(parents=True, exist_ok=True)


def _append(file: Path, record: dict):
    """Append a single JSON record as a new line in the JSONL file."""
    _ensure_dir()
    try:
        with open(file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.debug(f"[Trainer] Failed to write training record: {e}")


def _ts() -> str:
    return datetime.now().isoformat(timespec="seconds")


# ── Q&A Recorder ─────────────────────────────────────────────────────────────

def record_qa(
    question: str,
    answer: str,
    platform: str = "",
    listing_title: str = "",
    company: str = "",
    source: str = "ai",  # "ai", "cache", "india_field", "fallback"
):
    """
    Record a form question + the answer the bot filled in.
    Called by form_filler.py after every field is answered.

    Args:
        question:      The form field label / question text
        answer:        The answer that was filled in
        platform:      Platform name (internshala, linkedin, etc.)
        listing_title: Job/internship title being applied to
        company:       Company name
        source:        How the answer was generated
    """
    if not question or not answer:
        return
    record = {
        "timestamp": _ts(),
        "platform": platform,
        "company": company,
        "listing": listing_title,
        "question": question.strip(),
        "answer": answer.strip(),
        "source": source,
    }
    _append(TRAINING_DIR / "qa_pairs.jsonl", record)
    logger.debug(f"[Trainer] 📝 Q&A recorded: {question[:40]!r} → {answer[:30]!r}")


# ── Scoring Recorder ──────────────────────────────────────────────────────────

def record_score(
    listing: dict,
    score: int,
    reason: str,
    applied: bool,
    method: str = "ai",  # "ai", "keyword"
):
    """
    Record a listing scoring decision (apply / skip).
    Called by filter.py after every listing is scored.

    Args:
        listing: The full listing dict
        score:   Score 1–10
        reason:  Reason string from AI or keyword scorer
        applied: True if bot decided to apply, False if skip
        method:  "ai" or "keyword"
    """
    record = {
        "timestamp": _ts(),
        "platform": listing.get("source", ""),
        "title": listing.get("title", ""),
        "company": listing.get("company", ""),
        "location": listing.get("location", ""),
        "stipend": listing.get("stipend", ""),
        "duration": listing.get("duration", ""),
        "url": listing.get("apply_url", ""),
        "score": score,
        "reason": reason,
        "applied": applied,
        "method": method,
    }
    _append(TRAINING_DIR / "score_pairs.jsonl", record)
    emoji = "✅" if applied else "⏭️"
    logger.debug(f"[Trainer] {emoji} Score recorded: {listing.get('title', '?')} → {score}/10")


# ── Action Recorder ───────────────────────────────────────────────────────────

def record_action(
    action: str,
    platform: str = "",
    element: str = "",
    url: str = "",
    listing_title: str = "",
    company: str = "",
    extra: dict = None,
):
    """
    Record a bot action (click, navigate, submit, etc.).
    Call this when the bot takes any significant step.

    Args:
        action:        Action name e.g. "click_apply", "navigate", "submit", "form_fill"
        platform:      Platform name
        element:       Description of element clicked (e.g. "Apply Now button")
        url:           Current page URL
        listing_title: Job title (if applying)
        company:       Company name (if applying)
        extra:         Any additional context
    """
    record = {
        "timestamp": _ts(),
        "platform": platform,
        "action": action,
        "element": element,
        "url": url,
        "listing": listing_title,
        "company": company,
    }
    if extra:
        record.update(extra)
    _append(TRAINING_DIR / "actions.jsonl", record)
    logger.debug(f"[Trainer] 🖱️  Action recorded: {action} on {platform}")


# ── Stats ─────────────────────────────────────────────────────────────────────

def get_training_stats() -> dict:
    """Return a summary of training data collected so far."""
    stats = {}
    for name, file in [
        ("qa_pairs", TRAINING_DIR / "qa_pairs.jsonl"),
        ("score_pairs", TRAINING_DIR / "score_pairs.jsonl"),
        ("actions", TRAINING_DIR / "actions.jsonl"),
    ]:
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    count = sum(1 for line in f if line.strip())
                stats[name] = count
            except Exception:
                stats[name] = 0
        else:
            stats[name] = 0
    stats["training_dir"] = str(TRAINING_DIR.resolve())
    return stats
