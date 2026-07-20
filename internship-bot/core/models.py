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

from typing import List, Optional, Any
from pydantic import BaseModel, Field as PydanticField, field_validator, model_validator
import pydantic
from sqlmodel import SQLModel, Field, JSON
import sqlalchemy as sa
from sqlalchemy.types import JSON as sa_JSON


class User(SQLModel, table=True):
    __tablename__ = "users"
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    stripe_customer_id: Optional[str] = None
    tier: str = Field(default="free") # free or pro
    created_at: str = Field(default_factory=lambda: __import__("datetime").datetime.now().isoformat())

class UserProfile(SQLModel, table=True):
    """
    Strict database schema for user profiles, replacing data/profile.json.
    """
    __tablename__ = "user_profiles"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="users.id", index=True)
    
    name: str = "Unknown Candidate"
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
    keywords: List[str] = Field(default_factory=list, sa_column=sa.Column(sa_JSON))
    skills: List[str] = Field(default_factory=list, sa_column=sa.Column(sa_JSON))
    projects: List[str] = Field(default_factory=list, sa_column=sa.Column(sa_JSON))
    achievement: str = ""
    location_preferences: List[str] = Field(default_factory=lambda: ["work from home", "remote"], sa_column=sa.Column(sa_JSON))
    exclude_keywords: List[str] = Field(default_factory=list, sa_column=sa.Column(sa_JSON))

    # Employment details
    years_of_experience: str = "0"
    notice_period: str = "Immediate"
    current_ctc: str = "0"
    expected_ctc: str = "As per industry standards"
    willing_to_relocate: str = "Yes"
    preferred_mode: List[str] = Field(default_factory=lambda: ["remote"], sa_column=sa.Column(sa_JSON))
    open_to_hybrid: str = "Yes"
    work_authorization: str = "Indian Citizen"

    # Platform credentials (optional)
    internshala_email: str = ""
    linkedin_email: str = ""
    naukri_email: str = ""
    unstop_email: str = ""


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
    score: int = PydanticField(default=0, ge=0, le=10)
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

def profile_from_dict(data: dict) -> UserProfile:
    """Parse raw profile dict into a validated UserProfile."""
    return UserProfile.model_validate(data)


def listing_from_dict(data: dict) -> JobListing:
    """Parse a raw scraper dict into a validated JobListing."""
    return JobListing.model_validate(data)

# ── Database Models ──────────────────────────────────────────────────────────

class ApplicationLog(SQLModel, table=True):
    __tablename__ = "applications"
    __table_args__ = (
        sa.UniqueConstraint("platform", "apply_url", name="uq_platform_url"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="users.id", index=True)
    platform: str = Field(index=True)
    apply_url: str
    title: str = ""
    company: str = ""
    location: str = ""
    score: int = 0
    status: str = "success"  # 'success' or 'failed'
    message: str = ""
    dry_run: bool = False
    applied_at: str = Field(default_factory=lambda: __import__("datetime").datetime.now().isoformat())

class BotSchedule(SQLModel, table=True):
    __tablename__ = "schedules"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="users.id", index=True)
    platform: str = Field(index=True)
    enabled: bool = False
    run_interval_hours: int = 24
    max_applies_per_run: int = 15
    next_run: Optional[str] = None

class BrowserSession(SQLModel, table=True):
    __tablename__ = "sessions"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="users.id", index=True)
    platform: str = Field(index=True)
    captured_at: str = ""
    iv: List[int] = Field(sa_column=sa.Column(sa_JSON))
    encrypted_blob: List[int] = Field(sa_column=sa.Column(sa_JSON))

class RunEvent(SQLModel, table=True):
    __tablename__ = "run_events"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="users.id", index=True)
    run_id: str = Field(index=True)
    timestamp: str = Field(default_factory=lambda: __import__("datetime").datetime.now().isoformat())
    severity: str = "INFO"
    message: str
    traceback: Optional[str] = None

class JobQueue(SQLModel, table=True):
    __tablename__ = "job_queue"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="users.id", index=True)
    platform: str = Field(index=True)
    status: str = Field(default="pending", index=True) # pending, running, completed, failed
    dry_run: bool = False
    headless: bool = True
    created_at: str = Field(default_factory=lambda: __import__("datetime").datetime.now().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

class SystemSettings(SQLModel, table=True):
    """
    Stores global environment variables and API keys dynamically.
    Replaces the ephemeral .env file.
    """
    __tablename__ = "system_settings"
    key: str = Field(primary_key=True)
    value: str
