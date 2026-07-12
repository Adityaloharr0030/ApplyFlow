"""
agent/resume_brain.py
─────────────────────
Parses your resume PDF once, extracts structured data using Gemini AI,
and caches the result to data/resume_cache.json.

Every subsequent call uses the cache — no re-parsing needed.
The ResumeContext object is injected into all AI scoring and cover-note calls.

Usage:
    from agent.resume_brain import get_resume_context
    ctx = get_resume_context()       # returns ResumeContext
    print(ctx.summary_for_prompt())  # ready-to-paste into a Gemini prompt

Run standalone to test:
    python agent/resume_brain.py
"""

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

RESUME_PDF  = Path("./data/resume.pdf")
CACHE_FILE  = Path("./data/resume_cache.json")

# ── Resume data model ─────────────────────────────────────────────────────────

@dataclass
class ResumeContext:
    name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    degree: str = ""
    college: str = ""
    graduation_year: str = ""
    skills: list[str] = field(default_factory=list)
    projects: list[dict] = field(default_factory=list)   # [{name, techs, bullets}]
    achievements: list[str] = field(default_factory=list)
    raw_text: str = ""

    # ── Helpers ───────────────────────────────────────────────────────────────

    def top_skills(self, n: int = 8) -> str:
        return ", ".join(self.skills[:n])

    def project_names(self) -> list[str]:
        return [p.get("name", "") for p in self.projects]

    def best_project_for(self, role_title: str) -> dict:
        """Pick the most relevant project for a given role title."""
        title = role_title.lower()
        priority = {
            "flutter":    ["flutter", "mobile", "dart", "android", "ios"],
            "react":      ["react", "next", "frontend", "web", "ui"],
            "node":       ["node", "backend", "api", "express", "server"],
            "java":       ["java", "spring", "backend", "oop", "dsa"],
            "fullstack":  ["full stack", "fullstack", "full-stack", "mern"],
            "ai":         ["ai", "ml", "gemini", "llm", "chatbot"],
            "salesforce": ["salesforce", "crm", "soql"],
        }
        for proj_key, keywords in priority.items():
            if any(kw in title for kw in keywords):
                for proj in self.projects:
                    techs_lower = " ".join(proj.get("techs", [])).lower()
                    if proj_key in techs_lower or any(kw in techs_lower for kw in keywords):
                        return proj
        return self.projects[0] if self.projects else {}

    def summary_for_prompt(self, max_chars: int = 1800) -> str:
        """Return a compact resume summary ready to inject into an AI prompt."""
        proj_lines = []
        for p in self.projects:
            name = p.get("name", "")
            techs = ", ".join(p.get("techs", []))
            bullets = " ".join(p.get("bullets", [])[:2])
            proj_lines.append(f"  • {name} [{techs}]: {bullets}")

        summary = f"""RESUME — {self.name}
Education: {self.degree}, {self.college} ({self.graduation_year})
Skills: {', '.join(self.skills)}
Projects:
{chr(10).join(proj_lines)}
Achievements: {'; '.join(self.achievements)}"""

        return summary[:max_chars]

    def cover_note_block(self, role_title: str) -> str:
        """Return the candidate block to paste into a cover-note prompt."""
        proj = self.best_project_for(role_title)
        proj_name = proj.get("name", self.project_names()[0] if self.project_names() else "my recent project")
        proj_techs = ", ".join(proj.get("techs", [])[:4])
        return (
            f"Name: {self.name}\n"
            f"Degree: {self.degree}, graduating {self.graduation_year}\n"
            f"College: {self.college}\n"
            f"Skills: {self.top_skills(6)}\n"
            f"Key Project: {proj_name} ({proj_techs})\n"
            f"GitHub: https://github.com/Adityaloharaa0030\n"
            f"Achievement: {self.achievements[0] if self.achievements else ''}"
        )


# ── PDF text extraction ────────────────────────────────────────────────────────

def _extract_pdf_text(pdf_path: Path) -> str:
    try:
        import pdfplumber
        text = ""
        with pdfplumber.open(str(pdf_path)) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text += t + "\n"
        return text.strip()
    except Exception as e:
        logger.error(f"[ResumeBrain] PDF read failed: {e}")
        return ""


# ── Gemini-powered extraction ─────────────────────────────────────────────────

def _extract_with_ai(raw_text: str) -> dict:
    """Ask Gemini to parse the raw resume text into structured JSON."""
    from agent.ai_client import get_ai_response

    system = "You are a resume parser. Extract structured data from the raw resume text. Return ONLY valid JSON."
    prompt = f"""Parse this resume into structured JSON.

RAW RESUME TEXT:
{raw_text[:3000]}

Return ONLY this JSON format (no markdown, no explanation):
{{
  "name": "...",
  "email": "...",
  "phone": "...",
  "location": "...",
  "degree": "...",
  "college": "...",
  "graduation_year": "...",
  "skills": ["skill1", "skill2", ...],
  "projects": [
    {{
      "name": "Project Name",
      "techs": ["tech1", "tech2"],
      "bullets": ["key achievement 1", "key achievement 2"]
    }}
  ],
  "achievements": ["achievement 1", "achievement 2"]
}}"""

    try:
        text = get_ai_response(system, prompt, max_tokens=1500, response_format="json")
        if not text:
            return {}
        text = text.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception as e:
        logger.warning(f"[ResumeBrain] AI extraction failed: {e}")
        return {}


# ── Fallback: manual extraction from Aditya's known resume ───────────────────

def _fallback_context(raw_text: str) -> dict:
    """Hardcoded fallback if AI parsing fails — based on parsed resume."""
    return {
        "name": "Aditya Lohar",
        "email": "adityalohar00030@gmail.com",
        "phone": "+91 86250 41969",
        "location": "Jalgaon, Maharashtra",
        "degree": "B.Tech Computer Engineering",
        "college": "KBSCOE&T Jalgaon (DBATU Lonere)",
        "graduation_year": "2027",
        "skills": [
            "Flutter", "Dart", "Firebase", "Riverpod", "SQLite",
            "React", "Next.js", "Node.js", "Express", "MongoDB", "MySQL",
            "Java", "DSA", "Git", "Docker", "Postman", "Gemini API", "REST APIs",
            "Salesforce", "SOQL", "JWT", "OOP"
        ],
        "projects": [
            {
                "name": "Krushi Mitra — AI-Powered Farmer Assistance App",
                "techs": ["Flutter", "Firebase", "Riverpod", "Gemini API", "Claude API", "SQLite", "OpenWeatherMap"],
                "bullets": [
                    "Architected 11-feature production Flutter app: AI Crop Doctor, Chatbot, Live Mandi Prices, Weather, Soil Advisor.",
                    "Built Gemini multi-key load balancing with Claude fallback; Firebase OTP auth + offline Firestore-to-SQLite sync.",
                    "Full trilingual support (Hindi, Marathi, English) — Final-year B.Tech project under Prof. P.A. Patil, KBSCOE&T."
                ]
            },
            {
                "name": "CrazyXAni — Anime Streaming Platform",
                "techs": ["Next.js", "React", "Node.js", "MongoDB", "Anilist API"],
                "bullets": [
                    "Full-stack SSR streaming platform with Anilist API aggregation, search, MongoDB watchlist.",
                    "SEO-optimised via Next.js SSR; RESTful backend with real-time API calls and user session management."
                ]
            },
            {
                "name": "Inventory Management REST API",
                "techs": ["Node.js", "Express", "MySQL", "JWT", "Postman"],
                "bullets": [
                    "Secure full-CRUD REST API with JWT role-based auth and normalised MySQL schema.",
                    "All endpoints tested via Postman collections."
                ]
            },
            {
                "name": "Java OOP Console Application",
                "techs": ["Java", "OOP", "Collections", "Exception Handling"],
                "bullets": [
                    "Clean implementation of encapsulation, inheritance, polymorphism, ArrayList, HashMap.",
                    "Robust exception handling for maintainable production-style code."
                ]
            }
        ],
        "achievements": [
            "Top ~800 of 31,000+ participants at Meta PyTorch OpenEnv Hackathon",
            "Built Krushi Mitra — full production Flutter app with 11 features as final-year project",
            "Multi-key Gemini load balancing with Claude AI fallback in production app"
        ]
    }


# ── Main public API ────────────────────────────────────────────────────────────

def build_resume_context(force_refresh: bool = False) -> ResumeContext:
    """
    Build and cache the resume context.
    - If cache exists and force_refresh=False, loads from cache.
    - Otherwise parses the PDF and asks Gemini to structure it.
    """
    if not force_refresh and CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.info("[ResumeBrain] Loaded resume context from cache")
            ctx = ResumeContext(**{k: v for k, v in data.items() if k in ResumeContext.__dataclass_fields__})
            return ctx
        except Exception as e:
            logger.warning(f"[ResumeBrain] Cache load failed ({e}), re-parsing...")

    # Parse PDF
    if not RESUME_PDF.exists():
        logger.warning(f"[ResumeBrain] Resume PDF not found at {RESUME_PDF} — using fallback context")
        raw_text = ""
        data = _fallback_context("")
    else:
        logger.info(f"[ResumeBrain] Parsing {RESUME_PDF}...")
        raw_text = _extract_pdf_text(RESUME_PDF)
        if not raw_text:
            logger.warning("[ResumeBrain] PDF text extraction returned empty — using fallback")
            data = _fallback_context("")
        else:
            logger.info("[ResumeBrain] Asking Gemini to structure resume...")
            data = _extract_with_ai(raw_text)
            if not data or not data.get("name"):
                logger.warning("[ResumeBrain] AI extraction returned empty — using fallback")
                data = _fallback_context(raw_text)

    data["raw_text"] = raw_text[:4000]

    # Save cache
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.info(f"[ResumeBrain] Resume context cached → {CACHE_FILE}")

    ctx = ResumeContext(**{k: v for k, v in data.items() if k in ResumeContext.__dataclass_fields__})
    return ctx


# Module-level singleton — loaded once per process
_resume_context: ResumeContext | None = None

def get_resume_context(force_refresh: bool = False) -> ResumeContext:
    """Return the cached ResumeContext singleton. Thread-safe for single-process bots."""
    global _resume_context
    if _resume_context is None or force_refresh:
        _resume_context = build_resume_context(force_refresh=force_refresh)
    return _resume_context


# ── CLI test ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv
    load_dotenv()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")

    force = "--refresh" in sys.argv
    ctx = get_resume_context(force_refresh=force)

    print("\n" + "=" * 60)
    print("  RESUME BRAIN — Extracted Context")
    print("=" * 60)
    print(f"  Name:       {ctx.name}")
    print(f"  Email:      {ctx.email}")
    print(f"  Degree:     {ctx.degree}")
    print(f"  College:    {ctx.college}")
    print(f"  Grad Year:  {ctx.graduation_year}")
    print(f"  Skills:     {ctx.top_skills(10)}")
    print(f"\n  Projects ({len(ctx.projects)}):")
    for p in ctx.projects:
        print(f"    • {p.get('name')} [{', '.join(p.get('techs', [])[:4])}]")
    print(f"\n  Achievements:")
    for a in ctx.achievements:
        print(f"    • {a}")
    print("\n  -- Prompt Summary --")
    print(ctx.summary_for_prompt())
    print("\n  -- Best project for 'Flutter Developer' --")
    proj = ctx.best_project_for("Flutter Developer")
    print(f"  → {proj.get('name')}")
    print("=" * 60)
