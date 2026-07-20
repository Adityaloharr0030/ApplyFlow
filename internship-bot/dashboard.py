from dotenv import load_dotenv
load_dotenv()
import os
import sys
import time
import subprocess
import asyncio
import json
import re
import threading
from datetime import datetime, date
from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect, Depends
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import base64
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

app = FastAPI(title="ApplyFlow Dashboard API", version="2.0.0")

@app.on_event("startup")
def startup_event():
    from core.db import init_db
    try:
        init_db()  # Create all tables in the database
        print("Database initialized successfully.")
    except Exception as e:
        print(f"Failed to initialize database: {e}")

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

def verify_api_key(api_key: str = Depends(api_key_header)):
    # Local mode: completely skip API key verification since auth is removed
    return api_key

# Allow CORS for the Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
LOGS_DIR = BASE_DIR / "logs"
CSV_PATH = LOGS_DIR / "applications.csv"
SESSION_DIR = BASE_DIR / "data" / "sessions"
SESSION_DIR.mkdir(parents=True, exist_ok=True)

# Schedule files
SCHEDULE_CONFIG_FILE = BASE_DIR / "data" / "schedule_config.json"
VALID_WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
DEFAULT_SCHEDULE_CONFIG = {
    "enabled": False,
    "days": ["mon", "tue", "wed", "thu", "fri"],
    "time": "09:00",
    "dry_run": True,
}
TIME_PATTERN = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")

scheduler = BackgroundScheduler()
current_process: Optional[subprocess.Popen] = None
current_process_started_at: Optional[datetime] = None
current_process_lock = threading.Lock()

# ── Session State ──────────────────────────────────────────────────────────────
session_state = {
    "status": "idle",  # idle, running, paused
    "started_at": None,
    "current_platform": "",
    "current_listing": "",
    "current_step": "",
    "applied_count": 0,
    "skipped_count": 0,
    "error_count": 0,
    "events": [],
}
ws_clients: list[WebSocket] = []

STATIC_SALT = b"applyflow_salt"

def get_aesgcm_key():
    secret = os.getenv("SESSION_SECRET_KEY")
    if not secret:
        raise ValueError("SESSION_SECRET_KEY is missing from environment")
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=STATIC_SALT,
        iterations=100000,
    )
    return kdf.derive(secret.encode('utf-8'))

# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────
def get_latest_log_file() -> Path | None:
    log_files = list(LOGS_DIR.glob("run_*.log"))
    if not log_files:
        return None
    return max(log_files, key=os.path.getctime)

def load_csv() -> pd.DataFrame:
    if not CSV_PATH.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(CSV_PATH)
    except Exception:
        return pd.DataFrame()

def clean_dataframe_for_json(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df = df.where(pd.notnull(df), None)
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].apply(lambda v: v.isoformat() if v is not None else None)
    return df

def load_schedule_config() -> dict:
    try:
        if SCHEDULE_CONFIG_FILE.exists():
            with open(SCHEDULE_CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
                if isinstance(config, dict):
                    return {**DEFAULT_SCHEDULE_CONFIG, **config}
    except Exception:
        pass
    return DEFAULT_SCHEDULE_CONFIG.copy()

def save_schedule_config(config: dict):
    try:
        SCHEDULE_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SCHEDULE_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        raise Exception(f"Failed to save schedule config: {e}")

def validate_schedule_config(config: dict) -> dict:
    if not isinstance(config, dict):
        raise HTTPException(status_code=400, detail="Schedule config must be an object.")
    enabled = bool(config.get("enabled", False))
    dry_run = bool(config.get("dry_run", True))
    days = config.get("days")
    time_str = config.get("time")

    if not isinstance(days, list) or not days:
        raise HTTPException(status_code=400, detail="Days must be a non-empty list of weekday codes.")

    normalized_days = []
    for item in days:
        if not isinstance(item, str):
            raise HTTPException(status_code=400, detail="Each day code must be a string.")
        normalized = item.strip().lower()[:3]
        if normalized not in VALID_WEEKDAYS:
            raise HTTPException(status_code=400, detail=f"Invalid weekday code: {item}")
        normalized_days.append(normalized)

    if not isinstance(time_str, str) or not TIME_PATTERN.match(time_str):
        raise HTTPException(status_code=400, detail="Time must be a string in HH:MM 24h format.")

    return {
        "enabled": enabled,
        "days": sorted(set(normalized_days), key=VALID_WEEKDAYS.index),
        "time": time_str,
        "dry_run": dry_run,
    }

def get_next_scheduled_run() -> Optional[str]:
    if not scheduler.running or not scheduler.get_jobs():
        return None
    next_fire_times = [job.next_run_time for job in scheduler.get_jobs() if job.next_run_time is not None]
    if not next_fire_times:
        return None
    next_dt = min(next_fire_times)
    if next_dt.tzinfo is not None:
        next_dt = next_dt.astimezone()
    return next_dt.isoformat()

def clear_schedule_jobs():
    for job in scheduler.get_jobs():
        scheduler.remove_job(job.id)

def schedule_jobs_from_config(config: dict):
    clear_schedule_jobs()
    if not config.get("enabled", False):
        return
    hour, minute = map(int, config["time"].split(":"))
    for day in config["days"]:
        trigger = CronTrigger(day_of_week=day, hour=hour, minute=minute)
        scheduler.add_job(
            func=scheduled_run,
            trigger=trigger,
            id=f"applyflow_{day}_{config['time']}",
            replace_existing=True,
            name=f"ApplyFlow schedule {day} {config['time']}",
        )

def scheduled_run():
    config = load_schedule_config()
    with current_process_lock:
        if current_process is not None and current_process.poll() is None:
            print("[scheduler] Skipping scheduled run because bot is already running")
            return
    spawned = spawn_bot_process(dry_run=config.get("dry_run", True), headless=True)
    if spawned:
        print(f"[scheduler] Triggered scheduled bot run at {datetime.now().isoformat()}")
    else:
        print(f"[scheduler] Skipped scheduled bot run at {datetime.now().isoformat()} because another run is active")

def spawn_bot_process(dry_run: bool, headless: bool = True, platform: Optional[str] = None, run_now: bool = True):
    global current_process, current_process_started_at
    with current_process_lock:
        if current_process is not None and current_process.poll() is None:
            return False

        try:
            cmd = [sys.executable, "main.py"]
            if run_now:
                cmd.append("--run-now")   # Always run immediately when launched from dashboard
            if dry_run:
                cmd.append("--dry-run")
            if not headless:
                cmd.append("--headed")
            if platform and platform != "all":
                cmd.extend(["--platform", platform])
            
            LOGS_DIR.mkdir(parents=True, exist_ok=True)
            log_file = LOGS_DIR / f"run_{int(time.time())}.log"
            out_file = open(log_file, "w", encoding="utf-8")
            
            current_process = subprocess.Popen(
                cmd,
                stdout=out_file,
                stderr=subprocess.STDOUT,
                cwd=str(BASE_DIR)
            )
            current_process_started_at = datetime.now()
            
            session_state["status"] = "running"
            session_state["started_at"] = current_process_started_at.isoformat()
            session_state["applied_count"] = 0
            session_state["skipped_count"] = 0
            session_state["error_count"] = 0
            session_state["current_listing"] = ""
            session_state["current_step"] = ""
            session_state["current_platform"] = platform or "all"
            session_state["events"] = [{"timestamp": datetime.now().isoformat(), "type": "info", "message": f"Bot process launched (PID {current_process.pid}) — {'DRY RUN' if dry_run else 'LIVE'}"}]
            
            # Background watcher: resets session_state once the process exits
            proc_ref = current_process
            def _watch_process():
                proc_ref.wait()  # blocks until process exits
                exit_code = proc_ref.returncode
                # Only reset if this is still the current process (not a newer run)
                if current_process is proc_ref:
                    session_state["status"] = "idle"
                    session_state["current_platform"] = ""
                    session_state["current_step"] = ""
                    session_state["events"].append({
                        "timestamp": datetime.now().isoformat(),
                        "type": "info" if exit_code == 0 else "error",
                        "message": f"Bot process exited (code {exit_code})",
                    })
                print(f"[dashboard] Bot process exited with code {exit_code}")

            t = threading.Thread(target=_watch_process, daemon=True)
            t.start()
            
            return True
        except Exception as e:
            print(f"Failed to spawn bot run: {e}")
            session_state["status"] = "idle"
            return False

def stop_bot_process() -> bool:
    global current_process, current_process_started_at
    with current_process_lock:
        if current_process is None or current_process.poll() is not None:
            current_process = None
            current_process_started_at = None
            return False
        current_process.terminate()
        try:
            current_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            current_process.kill()
            current_process.wait()
        current_process = None
        current_process_started_at = None
        session_state["status"] = "idle"
        return True

@app.on_event("startup")
def startup_scheduler():
    from core.db import init_db
    init_db()
    
    config = load_schedule_config()
    if not SCHEDULE_CONFIG_FILE.exists():
        save_schedule_config(config)
    schedule_jobs_from_config(config)
    if not scheduler.running:
        scheduler.start()
    print(f"[api] Scheduler started; enabled={config.get('enabled')} next_run={get_next_scheduled_run()}")

# ──────────────────────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────────────────────
from pydantic import BaseModel, EmailStr
from core.db import get_session
from sqlmodel import Session
from core.models import User, UserProfile
from core.auth import get_password_hash, verify_password, create_access_token, get_current_user
from fastapi.security import OAuth2PasswordRequestForm

@app.get("/api/health")
def health_check():
    """Health check endpoint for Render's health monitoring."""
    return {"status": "ok", "service": "ApplyFlow API"}


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str = "Unknown Candidate"

@app.post("/api/auth/register")
def register_user(user: UserCreate, session: Session = Depends(get_session)):
    from sqlmodel import select
    if session.exec(select(User).where(User.email == user.email)).first():
        raise HTTPException(status_code=400, detail="Email already registered")
        
    db_user = User(email=user.email, hashed_password=get_password_hash(user.password))
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    
    db_profile = UserProfile(user_id=db_user.id, name=user.name)
    session.add(db_profile)
    session.commit()
    
    return {"message": "User registered successfully"}

@app.post("/api/auth/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)):
    from sqlmodel import select
    user = session.exec(select(User).where(User.email == form_data.username)).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
        
    access_token = create_access_token(data={"sub": user.id})
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/api/stats")
def get_stats(session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    from core.models import ApplicationLog
    from sqlmodel import select
    
    logs = session.exec(select(ApplicationLog).where(ApplicationLog.user_id == user.id)).all()
    
    if not logs:
        return {
            "total_applied": 0,
            "today_applied": 0,
            "platforms": {},
            "success_rate": 0,
            "recent": [],
            "session": session_state,
        }

    platforms = {}
    today_applied = 0
    import datetime
    today = datetime.datetime.now().date()
    
    for log in logs:
        # Platforms
        platforms[log.platform] = platforms.get(log.platform, 0) + 1
        
        # Today
        try:
            log_date = datetime.datetime.fromisoformat(log.applied_at).date()
            if log_date == today:
                today_applied += 1
        except:
            pass

    success_logs = [l for l in logs if l.status.lower() in ("success", "applied")]
    success_rate = int((len(success_logs) / len(logs)) * 100) if logs else 0
    
    recent = [l.model_dump() for l in sorted(logs, key=lambda x: x.applied_at, reverse=True)[:5]]

    return {
        "total_applied": len(logs),
        "today_applied": today_applied,
        "platforms": platforms,
        "success_rate": success_rate,
        "recent": recent,
        "session": session_state,
    }
@app.get("/api/applications")
def get_applications(session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    from core.models import ApplicationLog
    from sqlmodel import select
    
    logs = session.exec(select(ApplicationLog).where(ApplicationLog.user_id == user.id).order_by(ApplicationLog.id.desc())).all()
    
    if not logs:
        return {"metrics": {"total": 0, "applied": 0, "failed": 0, "manual": 0, "skipped": 0, "average_score": 0.0}, "applications": []}
    
    scores = [l.score for l in logs if l.score is not None]
    avg_score = sum(scores) / len(scores) if scores else 0.0
    
    applied = len([l for l in logs if l.status.lower() in ("success", "applied")])
    failed = len([l for l in logs if l.status.lower() in ("error", "failed")])
    skipped = len([l for l in logs if l.dry_run])
    
    metrics = {
        "total": len(logs),
        "applied": applied,
        "failed": failed,
        "manual": 0,
        "skipped": skipped,
        "average_score": round(avg_score, 1),
    }

    return {
        "metrics": metrics,
        "applications": [l.model_dump() for l in logs]
    }
@app.get("/api/history")
def get_history(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    platform: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user)
):
    from core.models import ApplicationLog
    from sqlmodel import select
    
    query = select(ApplicationLog).where(ApplicationLog.user_id == user.id)
    
    if platform:
        query = query.where(ApplicationLog.platform == platform)
    if status:
        query = query.where(ApplicationLog.status == status)
        
    query = query.order_by(ApplicationLog.id.desc())
    logs = session.exec(query).all()
    
    total = len(logs)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_logs = logs[start_idx:end_idx]

    return {
        "items": [l.model_dump() for l in paginated_logs],
        "total": total,
        "page": page,
        "per_page": per_page
    }
@app.get("/api/history/applications")
def get_history():
    from core.db import engine
    from sqlmodel import Session, select
    from core.models import ApplicationLog
    try:
        with Session(engine) as session:
            # Get the last 100 applications, newest first
            statement = select(ApplicationLog).order_by(ApplicationLog.id.desc()).limit(100)
            results = session.exec(statement).all()
            # Convert SQLModel objects to dicts
            return [row.model_dump() for row in results]
    except Exception as e:
        print(f"Failed to fetch history: {e}")
        return []

# ── Profile & Settings Endpoints ─────────────────────────────────────────────

PROFILE_PATH = BASE_DIR / "data" / "profile.json"
ENV_PATH = BASE_DIR / ".env"

@app.get("/api/profile")
def get_profile(session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    from sqlmodel import select
    from core.models import UserProfile
    profile = session.exec(select(UserProfile).where(UserProfile.user_id == user.id)).first()
    if not profile:
        return {}
    return profile.model_dump()

@app.post("/api/profile")
async def save_profile(data: dict, session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    from sqlmodel import select
    from core.models import UserProfile
    try:
        profile = session.exec(select(UserProfile).where(UserProfile.user_id == user.id)).first()
        if profile:
            for key, value in data.items():
                if hasattr(profile, key):
                    setattr(profile, key, value)
            session.add(profile)
        else:
            profile_data = {k: v for k, v in data.items() if hasattr(UserProfile, k)}
            profile = UserProfile(user_id=user.id, **profile_data)
            session.add(profile)
            
        session.commit()
        return {"status": "success", "message": "Profile saved to database."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from fastapi import UploadFile, File
import io

@app.post("/api/profile/parse-resume")
async def parse_resume(file: UploadFile = File(...), user: User = Depends(get_current_user)):
    import pypdf
    from agent.ai_client import get_ai_response
    import json
    
    try:
        pdf_bytes = await file.read()
        pdf_reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"

        prompt = f"""
        You are an expert resume parser. Extract the following information from the resume and output ONLY a valid JSON object matching this exact schema:
        {{
            "name": "Full Name",
            "email": "Email Address",
            "phone": "Phone Number",
            "location": "City, State, Country",
            "degree": "Highest Degree (e.g., B.Tech, B.S.)",
            "college": "University Name",
            "year": "Graduation Year",
            "cgpa": "GPA or CGPA",
            "linkedin": "LinkedIn URL",
            "github": "GitHub URL",
            "skills": "Comma separated list of skills",
            "projects": "Comma separated list of projects",
            "years_of_experience": "Number of years",
            "achievement": "Top achievement"
        }}

        If a field is missing in the resume, leave it as an empty string. Output ONLY JSON, nothing else. No markdown formatting.
        
        Resume Text:
        {text}
        """
        
        response = get_ai_response(
            system_prompt="You are a helpful API that returns strictly valid JSON data.",
            user_prompt=prompt,
            max_tokens=1000,
            response_format="json",
            user_id=user.id
        )
        
        if response:
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
                
            data = json.loads(response)
            return {"status": "success", "data": data}
        
        raise HTTPException(status_code=500, detail="Failed to get AI response")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse resume: {str(e)}")

@app.get("/api/settings")
def get_settings(session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    from core.models import UserSettings
    # Load user specific keys from DB
    db_settings = session.exec(select(UserSettings).where(UserSettings.user_id == user.id)).all()
    settings_dict = {s.key: s.value for s in db_settings}
    
    # Also include os.environ for keys that are set globally in Render (so UI shows them)
    for k, v in os.environ.items():
        if k in ["GROQ_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY", "WHATSAPP_PHONE", "WHATSAPP_API_KEY", "DATABASE_URL"]:
            if k not in settings_dict:
                settings_dict[k] = v
                
    return settings_dict

@app.post("/api/settings")
def save_settings(data: dict, session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    from core.models import UserSettings
    import os
    try:
        for k, v in data.items():
            setting = session.exec(select(UserSettings).where(UserSettings.key == k, UserSettings.user_id == user.id)).first()
            if setting:
                setting.value = str(v)
                session.add(setting)
            else:
                setting = UserSettings(user_id=user.id, key=k, value=str(v))
                session.add(setting)
            
            # NOTE: We DO NOT update os.environ anymore because API keys are now user-specific!
        
        session.commit()
        return {"status": "success", "message": "Settings saved to database."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── Interview Prep Endpoints ──────────────────────────────────────────────────

PREP_DIR = BASE_DIR / "logs" / "prep"

@app.get("/api/prep")
def list_prep_guides():
    PREP_DIR.mkdir(parents=True, exist_ok=True)
    files = []
    for f in sorted(PREP_DIR.glob("*.txt"), key=lambda x: x.stat().st_mtime, reverse=True):
        stat = f.stat()
        files.append({
            "filename": f.name,
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        })
    return files

@app.get("/api/prep/{filename}")
def get_prep_guide(filename: str):
    PREP_DIR.mkdir(parents=True, exist_ok=True)
    # Security: only allow .txt files with no path traversal
    if ".." in filename or "/" in filename or not filename.endswith(".txt"):
        raise HTTPException(status_code=400, detail="Invalid filename")
    path = PREP_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return {"filename": filename, "content": path.read_text(encoding="utf-8")}

class GeneratePrepRequest(BaseModel):
    job_description: str
    role: str

@app.post("/api/prep/generate")
def generate_prep(req: GeneratePrepRequest):
    try:
        from agent.ai_client import get_ai_response
        system_prompt = "You are an expert interview coach. Given the role and job description, generate a concise, actionable interview prep guide. Focus on likely technical questions, behavioral themes, and key company context. Format with clear Markdown headings."
        user_prompt = f"Role: {req.role}\n\nJob Description:\n{req.job_description}"
        response = get_ai_response(system_prompt, user_prompt, max_tokens=1500)
        
        # Save it
        filename = f"{re.sub(r'[^a-zA-Z0-9]', '_', req.role).lower()}_{int(time.time())}.txt"
        path = PREP_DIR / filename
        PREP_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(response, encoding="utf-8")
        
        return {"status": "success", "filename": filename, "content": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Platforms Endpoints ───────────────────────────────────────────────────────

PLATFORMS_PATH = BASE_DIR / "data" / "platforms.json"
DEFAULT_PLATFORMS = {
    "internshala": {"enabled": True, "max_applies": 10},
    "linkedin": {"enabled": True, "max_applies": 15},
    "indeed": {"enabled": True, "max_applies": 10},
    "unstop": {"enabled": True, "max_applies": 5},
    "naukri": {"enabled": True, "max_applies": 10},
    "cold_email": {"enabled": False, "max_applies": 5},
}

@app.get("/api/platforms")
def get_platforms():
    if PLATFORMS_PATH.exists():
        try:
            with open(PLATFORMS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Merge with defaults for any missing platforms
            for k, v in DEFAULT_PLATFORMS.items():
                if k not in data:
                    data[k] = v
            return data
        except Exception:
            pass
    return DEFAULT_PLATFORMS

@app.post("/api/platforms")
def save_platforms(data: dict):
    try:
        PLATFORMS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(PLATFORMS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("dashboard:app", host="0.0.0.0", port=8000, reload=True)

