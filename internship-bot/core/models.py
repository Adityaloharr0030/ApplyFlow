"""
core/models.py
──────────────
Pydantic V2 data models for ApplyFlow.

All inter-module data exchange goes through these strict schemas.
This replaces loose dict passing and provides:
  - Automatic type coercion and validation at boundary
  - Clear field defaults so KeyError never occurs
  - IDE autocomplete / type safety throughout the codebase
"""

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


# ── Candidate Profile ──────────────────────────────────────────────────────────

class CandidateProfile(BaseModel):
    """
    Strict schema for data/profile.json.
    Loaded once at startup; passed (read-only) through the pipeline.
    """
    name: str = "Unknown Candidate"
    email: str = ""
    phone: str = ""
    location: str = ""
    degree: str = ""
    college: str = ""
    year: str = ""
    cgpa: str = ""
    gender: str = ""
    dob: str = ""

    # Resume & Links
    resume_path: str = ""
    linkedin: str = ""
    github: str = ""

    # Job preferences
    keywords: List[str] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    projects: List[str] = Field(default_factory=list)
    achievement: str = ""
    location_preferences: List[str] = Field(default_factory=lambda: ["work from home", "remote"])
    exclude_keywords: List[str] = Field(default_factory=list)

    # Employment details
    years_of_experience: str = "0"
    notice_period: str = "Immediate"
    current_ctc: str = "0"
    expected_ctc: str = "As per industry standards"
    willing_to_relocate: str = "Yes"
    preferred_mode: List[str] = Field(default_factory=lambda: ["remote"])
    open_to_hybrid: str = "Yes"
    work_authorization: str = "Indian Citizen"

    # Platform credentials (optional — loaded from .env, not profile.json)
    internshala_email: str = ""
    linkedin_email: str = ""
    naukri_email: str = ""
    unstop_email: str = ""

    @field_validator("keywords", "skills", "projects", "location_preferences",
                     "exclude_keywords", "preferred_mode", mode="before")
    @classmethod
    def ensure_list(cls, v):
        if isinstance(v, str):
            return [v] if v else []
        return v or []

    @field_validator("email")
    @classmethod
    def not_placeholder_email(cls, v):
        if v in ("youremail@example.com", ""):
            return v  # warn at runtime, don't crash
        return v

    class Config:
        extra = "allow"  # forward-compatible: unknown keys in profile.json are ignored


# ── Job Listing ────────────────────────────────────────────────────────────────

class JobListing(BaseModel):
    """
    Strict schema for a scraped job/internship listing.
    Produced by platform scrapers; consumed by filter, cover note, and apply.
    """
    title: str = ""
    company: str = ""
    location: str = ""
    description: str = ""
    apply_url: str = ""
    platform: str = ""

    # Scoring fields — populated by agent/filter.py
    score: int = Field(default=0, ge=0, le=10)
    reason: str = ""
    apply: bool = False

    # Metadata
    stipend: str = ""
    duration: str = ""
    posted_at: str = ""

    @field_validator("title", "company", "location", "description", mode="before")
    @classmethod
    def strip_strings(cls, v):
        return (v or "").strip()

    @field_validator("score", mode="before")
    @classmethod
    def clamp_score(cls, v):
        try:
            return max(0, min(10, int(v)))
        except (ValueError, TypeError):
            return 0


# ── Application Result ─────────────────────────────────────────────────────────

class ApplicationResult(BaseModel):
    """
    Returned by every platform's apply() method.
    Replaces the loose {"success": bool, "message": str} dicts.
    """
    success: bool = False
    message: str = ""
    platform: str = ""
    listing_title: str = ""
    listing_company: str = ""
    apply_url: str = ""
    dry_run: bool = False

    def __bool__(self) -> bool:
        return self.success

    @classmethod
    def ok(cls, message: str = "Applied successfully", **kwargs) -> "ApplicationResult":
        return cls(success=True, message=message, **kwargs)

    @classmethod
    def fail(cls, message: str = "Application failed", **kwargs) -> "ApplicationResult":
        return cls(success=False, message=message, **kwargs)

    @classmethod
    def dry(cls, **kwargs) -> "ApplicationResult":
        return cls(success=True, message="Dry run — not submitted", dry_run=True, **kwargs)


# ── Helpers ────────────────────────────────────────────────────────────────────

def profile_from_dict(data: dict) -> CandidateProfile:
    """Parse raw profile.json dict into a validated CandidateProfile."""
    return CandidateProfile.model_validate(data)


def listing_from_dict(data: dict) -> JobListing:
    """Parse a raw scraper dict into a validated JobListing."""
    return JobListing.model_validate(data)
