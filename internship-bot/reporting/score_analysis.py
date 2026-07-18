"""
reporting/score_analysis.py
────────────────────────────
Phase C/D: Score distribution analysis.

Reads logs/applications.csv and produces:
  1. Score histograms per platform
  2. Callback rate analysis (when CALLBACK_DATE is present)
  3. Detects scoring drift between platforms

Usage:
    python reporting/score_analysis.py

Or from Python:
    from reporting.score_analysis import generate_report
    report = generate_report()
    print(report)
"""

import logging
from collections import defaultdict
from pathlib import Path

logger = logging.getLogger(__name__)

CSV_PATH = Path("./logs/applications.csv")


def generate_report() -> str:
    """
    Read applications.csv and return a formatted analysis string.
    Safe to call even if csv doesn't exist yet.
    """
    if not CSV_PATH.exists():
        return "[ScoreAnalysis] No applications.csv found yet — run the bot first."

    try:
        import pandas as pd
    except ImportError:
        return "[ScoreAnalysis] pandas not installed — run: pip install pandas"

    df = pd.read_csv(CSV_PATH)

    # Normalise column names to lowercase so lookups work regardless of CSV casing.
    # Also map the CSV's "Source" column → "platform" to match the rest of the report.
    df.columns = [c.strip() for c in df.columns]
    col_rename = {}
    for c in df.columns:
        col_rename[c] = c.lower()
    df = df.rename(columns=col_rename)

    # CSV uses "source" (scraped from "Source" header) — expose it as "platform"
    if "source" in df.columns and "platform" not in df.columns:
        df["platform"] = df["source"]

    # "apply url" → "apply_url", "cover note preview" → "cover_note_preview"
    df.columns = [c.replace(" ", "_") for c in df.columns]

    lines = ["", "=" * 60, "  ApplyFlow — Score Distribution Report", "=" * 60]

    # ── Platform counts ────────────────────────────────────────────
    if "platform" in df.columns:
        lines.append("\n[1] Applications per Platform:")
        counts = df["platform"].value_counts()
        for plat, cnt in counts.items():
            lines.append(f"    {plat:<20} {cnt:>4} applications")

    # ── Score distributions ────────────────────────────────────────
    if "score" in df.columns and "platform" in df.columns:
        lines.append("\n[2] Mean AI Score per Platform (potential scoring drift):")
        score_df = df.dropna(subset=["score"])
        score_df = score_df[pd.to_numeric(score_df["score"], errors="coerce").notna()].copy()
        score_df["score"] = pd.to_numeric(score_df["score"])
        by_platform = score_df.groupby("platform")["score"].agg(["mean", "std", "count"])
        for plat, row in by_platform.iterrows():
            flag = " ⚠️ DRIFT" if abs(row["mean"] - by_platform["mean"].mean()) > 1.5 else ""
            lines.append(
                f"    {plat:<20} mean={row['mean']:.1f}  std={row['std']:.2f}"
                f"  n={int(row['count'])}{flag}"
            )

    # ── Status breakdown ───────────────────────────────────────────
    if "status" in df.columns:
        lines.append("\n[3] Status Breakdown:")
        for status, cnt in df["status"].value_counts().items():
            pct = 100 * cnt / len(df)
            lines.append(f"    {status:<30} {cnt:>4} ({pct:.0f}%)")

    # ── Callback analysis ──────────────────────────────────────────
    if "callback_date" in df.columns:
        cb = df.dropna(subset=["callback_date"])
        cb = cb[cb["callback_date"].astype(str).str.strip() != ""]
        total_applied = int(df["status"].str.contains("Applied|Success", case=False, na=False).sum()) if "status" in df.columns else 0
        cb_rate = 100 * len(cb) / total_applied if total_applied else 0
        lines.append(f"\n[4] Callback Rate: {len(cb)} / {total_applied} ({cb_rate:.1f}%)")
        if len(cb) > 0 and "platform" in df.columns:
            lines.append("    By Platform:")
            for plat, grp in cb.groupby("platform"):
                total_plat = len(df[df["platform"] == plat])
                lines.append(f"    {plat:<20} {len(grp)} callbacks / {total_plat} applied")
    else:
        lines.append(
            "\n[4] Callback Rate: N/A — Add a 'Callback_Date' column to "
            "applications.csv when you receive interview invites to enable this."
        )

    lines.append("\n" + "=" * 60)
    return "\n".join(lines)


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    print(generate_report())
