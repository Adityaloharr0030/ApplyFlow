"""
agent/outcome_tracker.py
────────────────────────
Learns from past application outcomes in logs/applications.csv.

Extracts:
  - good_keywords : role title words that led to "Applied ✓"
  - bad_companies : companies that consistently error-blocked (CAPTCHA, driver fail)
  - already_applied: set of (company, role) tuples already attempted this week
  - platform_success_rate: % success per platform

This context is injected into the AI scoring prompt so the model knows
what roles have been successfully applied to before.

Usage:
    from agent.outcome_tracker import get_outcome_context
    ctx = get_outcome_context()
    print(ctx.scoring_hint())    # inject into Gemini prompt
    print(ctx.is_duplicate(company, role))  # skip duplicates

Run standalone:
    python agent/outcome_tracker.py
"""

import logging
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

CSV_PATH = Path("./logs/applications.csv")

# ── Data model ────────────────────────────────────────────────────────────────

class OutcomeContext:
    def __init__(self):
        self.total: int = 0
        self.applied_count: int = 0
        self.callback_rate: float = 0.0          # % of submissions that got a callback
        self.good_title_keywords: list[str] = []   # title words associated with success
        self.bad_companies: set[str] = set()        # companies that always error-blocked
        self.bad_domains: set[str] = set()          # domains that always redirect externally
        self.already_applied: set[tuple] = set()    # (company_lower, role_lower) this week
        self.platform_rates: dict[str, float] = {}  # platform → success rate %
        self.avg_score_applied: float = 0.0         # avg score of successful applications
        self.top_applied_roles: list[str] = []      # most common role titles applied to

    def is_duplicate(self, company: str, role: str) -> bool:
        """Return True if we already applied to this (company, role) this week."""
        key = (company.lower().strip(), role.lower().strip())
        return key in self.already_applied

    def is_bad_company(self, company: str) -> bool:
        return company.lower().strip() in self.bad_companies

    def scoring_hint(self, max_chars: int = 600) -> str:
        """Return a short context block to inject into the AI scoring prompt."""
        lines = []
        if self.good_title_keywords:
            lines.append(f"SUCCESSFUL ROLE KEYWORDS (apply aggressively): {', '.join(self.good_title_keywords[:12])}")
        if self.top_applied_roles:
            lines.append(f"TOP APPLIED ROLES: {', '.join(self.top_applied_roles[:5])}")
        if self.bad_companies:
            lines.append(f"AVOID THESE COMPANIES (always error/CAPTCHA): {', '.join(list(self.bad_companies)[:8])}")
        if self.platform_rates:
            rates = [f"{p}: {r:.0f}%" for p, r in sorted(self.platform_rates.items(), key=lambda x: -x[1])]
            lines.append(f"PLATFORM SUCCESS RATES: {', '.join(rates)}")
        lines.append(f"ALREADY APPLIED THIS WEEK: {len(self.already_applied)} roles — skip exact duplicates")
        return "\n".join(lines)[:max_chars]


# ── Builder ──────────────────────────────────────────────────────────────────

def _extract_title_keywords(titles: list[str]) -> list[str]:
    """Extract meaningful single/bigram keywords from role titles."""
    stop = {
        "intern", "internship", "developer", "engineer", "manager",
        "senior", "junior", "lead", "associate", "trainee", "and", "the",
        "for", "at", "in", "of", "with", "cum", "or", "-"
    }
    counter: Counter = Counter()
    for title in titles:
        words = re.findall(r"[a-zA-Z]+", title.lower())
        for w in words:
            if w not in stop and len(w) > 2:
                counter[w] += 1
        # bigrams
        for a, b in zip(words, words[1:]):
            if a not in stop and b not in stop:
                counter[f"{a} {b}"] += 1

    # Return top keywords seen in ≥2 successful applications
    return [kw for kw, count in counter.most_common(20) if count >= 2]


def build_outcome_context(days_back: int = 30) -> OutcomeContext:
    """
    Load applications.csv and build an OutcomeContext.
    days_back: how far back to look for "already applied" duplicate detection.
    """
    ctx = OutcomeContext()

    if not CSV_PATH.exists():
        logger.info("[OutcomeTracker] No CSV found — starting fresh")
        return ctx

    try:
        df = pd.read_csv(CSV_PATH)
    except Exception as e:
        logger.warning(f"[OutcomeTracker] Could not load CSV: {e}")
        return ctx

    ctx.total = len(df)
    if ctx.total == 0:
        return ctx

    # Normalise column names (strip whitespace)
    df.columns = [c.strip() for c in df.columns]

    # Ensure required columns
    for col in ["Status", "Company", "Role", "Source", "Score", "Date"]:
        if col not in df.columns:
            df[col] = ""

    df["Status"] = df["Status"].fillna("").astype(str)
    df["Company"] = df["Company"].fillna("").astype(str)
    df["Role"] = df["Role"].fillna("").astype(str)
    df["Source"] = df["Source"].fillna("").astype(str)
    df["Score"] = pd.to_numeric(df["Score"], errors="coerce").fillna(0)

    # ── Identify successful applications ──────────────────────────────────────
    applied_mask = df["Status"].str.contains("Applied|Success", case=False, na=False)
    applied_df = df[applied_mask]
    ctx.applied_count = len(applied_df)

    # Phase D fix: Prefer callback-confirmed applications for keyword learning.
    # If a 'callback_date' column exists, learn exclusively from those rows
    # (prevents the bot from optimising for "easy to submit" rather than "callback-likely").
    if "Callback_Date" in df.columns or "callback_date" in df.columns:
        cb_col = "Callback_Date" if "Callback_Date" in df.columns else "callback_date"
        callback_df = df[df[cb_col].notna() & (df[cb_col].astype(str).str.strip() != "")]
        callback_df = callback_df[callback_df["Status"].str.contains("Applied|Success", case=False, na=False)]

        if len(callback_df) >= 3:
            # Enough callbacks to learn from — use them exclusively
            learn_df = callback_df
            ctx.callback_rate = round(100 * len(callback_df) / max(ctx.applied_count, 1), 1)
            logger.info(
                "[OutcomeTracker] Using %d callback-confirmed rows for keyword learning (callback_rate=%.1f%%)",
                len(learn_df), ctx.callback_rate
            )
        else:
            # Fallback: not enough callbacks yet — use all submissions (old behaviour)
            learn_df = applied_df
            logger.info(
                "[OutcomeTracker] Insufficient callbacks (%d) — learning from all %d submissions",
                len(callback_df), ctx.applied_count
            )
    else:
        learn_df = applied_df
        logger.debug("[OutcomeTracker] No callback_date column — learning from submissions (add column to improve accuracy)")

    if len(learn_df) > 0:
        ctx.good_title_keywords = _extract_title_keywords(learn_df["Role"].tolist())
        ctx.avg_score_applied = float(learn_df["Score"].mean())
        ctx.top_applied_roles = (
            learn_df["Role"]
            .str.lower()
            .str.strip()
            .value_counts()
            .head(5)
            .index.tolist()
        )

    # ── Identify error-blocked companies (≥3 errors, 0 successes) ──
    error_mask = df["Status"].str.contains("Error|CAPTCHA|Blocked|Failed", case=False, na=False)
    error_df = df[error_mask]

    company_errors = error_df["Company"].str.lower().str.strip().value_counts()
    company_applied = applied_df["Company"].str.lower().str.strip().value_counts()

    for company, error_count in company_errors.items():
        if error_count >= 3 and company not in company_applied.index:
            ctx.bad_companies.add(company)

    # ── Platform success rates ──
    for platform in df["Source"].str.lower().str.strip().unique():
        if not platform:
            continue
        platform_df = df[df["Source"].str.lower().str.strip() == platform]
        total = len(platform_df)
        if total == 0:
            continue
        success = len(platform_df[platform_df["Status"].str.contains("Applied|Success", case=False, na=False)])
        ctx.platform_rates[platform.title()] = round((success / total) * 100, 1)

    # ── Already applied this week (duplicate detection) ──
    cutoff = datetime.now() - timedelta(days=days_back)
    try:
        df["_date"] = pd.to_datetime(df["Date"], errors="coerce")
        recent_df = df[df["_date"] >= cutoff]
        for _, row in recent_df.iterrows():
            co = str(row["Company"]).lower().strip()
            ro = str(row["Role"]).lower().strip()
            if co and ro:
                ctx.already_applied.add((co, ro))
    except Exception as e:
        logger.debug(f"[OutcomeTracker] Date parsing issue: {e}")

    logger.info(
        f"[OutcomeTracker] Loaded: {ctx.total} total, {ctx.applied_count} applied, "
        f"{len(ctx.bad_companies)} bad companies, {len(ctx.already_applied)} recent pairs"
    )
    return ctx


# Module-level singleton
_outcome_context: OutcomeContext | None = None

def get_outcome_context(force_refresh: bool = False) -> OutcomeContext:
    global _outcome_context
    if _outcome_context is None or force_refresh:
        _outcome_context = build_outcome_context()
    return _outcome_context


# ── CLI test ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    ctx = get_outcome_context()

    print("\n" + "=" * 60)
    print("  OUTCOME TRACKER — Learned Patterns")
    print("=" * 60)
    print(f"  Total applications: {ctx.total}")
    print(f"  Successfully applied: {ctx.applied_count}")
    print(f"  Avg score of applied: {ctx.avg_score_applied:.1f}/10")
    print(f"  Top applied roles: {', '.join(ctx.top_applied_roles[:5])}")
    print(f"\n  Good title keywords ({len(ctx.good_title_keywords)}):")
    print(f"    {', '.join(ctx.good_title_keywords[:15])}")
    print(f"\n  Bad companies ({len(ctx.bad_companies)}):")
    for c in list(ctx.bad_companies)[:10]:
        print(f"    • {c}")
    print(f"\n  Platform success rates:")
    for p, r in sorted(ctx.platform_rates.items(), key=lambda x: -x[1]):
        print(f"    {p}: {r:.1f}%")
    print(f"\n  Already applied this period: {len(ctx.already_applied)} (company, role) pairs")
    print("\n  -- Scoring Hint for AI --")
    print(ctx.scoring_hint())
    print("=" * 60)
