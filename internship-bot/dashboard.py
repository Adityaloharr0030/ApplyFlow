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
    from core.db import engine, init_db
    from core.models import SystemSettings
    from sqlmodel import Session, select
    import os
    try:
        init_db()  # Ensure tables exist
        with Session(engine) as session:
            settings = session.exec(select(SystemSettings)).all()
            for setting in settings:
                os.environ[setting.key] = setting.value
        print("Loaded SystemSettings into os.environ")
    except Exception as e:
        print(f"Failed to load SystemSettings into os.environ: {e}")

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
def get_stats():
    df = load_csv()
    if df.empty:
        return {
            "total_applied": 0,
            "today_applied": 0,
            "platforms": {},
            "success_rate": 0,
            "recent": [],
            "session": session_state,
        }

    try:
        platforms = {}
        platform_col = "Platform" if "Platform" in df.columns else "Source" if "Source" in df.columns else None
        if platform_col:
            platforms = {str(k): int(v) for k, v in df[platform_col].value_counts().to_dict().items()}

        today_applied = 0
        if "Date" in df.columns:
            today_str = datetime.now().strftime("%Y-%m-%d")
            today_applied = len(df[df["Date"].astype(str).str.startswith(today_str, na=False)])

        success_rate = 0
        if "Status" in df.columns:
            total = len(df)
            successes = len(df[df["Status"].astype(str).str.lower().isin(["applied", "success", "submitted"])])
            success_rate = round((successes / total * 100) if total > 0 else 0, 1)

        recent = clean_dataframe_for_json(df.tail(10)).to_dict(orient="records")[::-1]

        return {
            "total_applied": int(len(df)),
            "today_applied": int(today_applied),
            "platforms": platforms,
            "success_rate": float(success_rate),
            "recent": recent,
            "session": session_state,
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/applications")
def get_applications():
    df = load_csv()
    if df.empty:
        return {"metrics": {"total": 0, "applied": 0, "failed": 0, "manual": 0, "skipped": 0, "average_score": 0.0}, "applications": []}
    
    scores = pd.to_numeric(df.get("Score", pd.Series(dtype=float)), errors="coerce")
    avg_score = float(scores.mean()) if not scores.isna().all() else 0.0

    metrics = {
        "total": len(df),
        "applied": int(df.get("Status", pd.Series(dtype=str)).str.contains("Applied|Success", case=False, na=False).sum()),
        "failed": int(df.get("Status", pd.Series(dtype=str)).str.contains("Error|Failed", case=False, na=False).sum()),
        "manual": int(df.get("Status", pd.Series(dtype=str)).str.contains("Manual|Pending", case=False, na=False).sum()),
        "skipped": int(df.get("Status", pd.Series(dtype=str)).str.contains("Skipped|Dry Run", case=False, na=False).sum()),
        "average_score": round(avg_score, 1),
    }

    try:
        applications = clean_dataframe_for_json(df).to_dict(orient="records")[::-1]
    except Exception:
        applications = []
    
    return {"metrics": metrics, "applications": applications}


@app.get("/api/runs")
def get_runs():
    """
    Return all bot runs grouped by log file / run date.
    Each run contains metadata (date, stats) + the applications recorded during it.
    """
    df = load_csv()
    if df.empty:
        return {"runs": []}

    try:
        # Parse dates; group by the date part to identify each run
        df["_date"] = pd.to_datetime(df.get("Date", pd.Series(dtype=str)), errors="coerce")
        df["_day"] = df["_date"].dt.strftime("%Y-%m-%d")

        # Match each day to its log file for metadata
        log_files: dict[str, dict] = {}
        for lf in sorted(LOGS_DIR.glob("run_*.log"), reverse=True):
            stem = lf.stem  # e.g. run_2026-07-19
            day = stem.replace("run_", "")
            if len(day) == 10:  # YYYY-MM-DD format
                mtime = datetime.fromtimestamp(lf.stat().st_mtime)
                size_kb = lf.stat().st_size // 1024
                log_files[day] = {
                    "log_file": lf.name,
                    "log_size_kb": size_kb,
                    "ended_at": mtime.isoformat(),
                }

        runs = []
        for day, group in df.groupby("_day", sort=False):
            if not day or day == "NaT":
                continue

            status_col = group.get("Status", pd.Series(dtype=str)).fillna("").str.lower()
            applied  = int(status_col.str.contains("applied|success").sum())
            errors   = int(status_col.str.contains("error|failed").sum())
            skipped  = int(status_col.str.contains("skipped|dry run").sum())
            manual   = int(status_col.str.contains("manual|pending").sum())

            scores   = pd.to_numeric(group.get("Score", pd.Series(dtype=float)), errors="coerce")
            avg_sc   = round(float(scores.mean()), 1) if not scores.isna().all() else 0.0

            platforms = list(group.get("Source", pd.Series(dtype=str)).dropna().unique())

            # Timestamps
            valid_dates = group["_date"].dropna()
            started_at = valid_dates.min().isoformat() if not valid_dates.empty else None
            ended_at   = valid_dates.max().isoformat() if not valid_dates.empty else None

            # Duration in minutes
            if started_at and ended_at and started_at != ended_at:
                duration_mins = int((valid_dates.max() - valid_dates.min()).total_seconds() / 60)
            else:
                duration_mins = None

            # Override ended_at from log file mtime if available
            log_meta = log_files.get(day, {})
            if log_meta.get("ended_at"):
                ended_at = log_meta["ended_at"]

            # Applications list (newest first within the run)
            apps_clean = clean_dataframe_for_json(
                group.sort_values("_date", ascending=False)
            ).drop(columns=["_date", "_day"], errors="ignore").to_dict(orient="records")

            runs.append({
                "date": day,
                "started_at": started_at,
                "ended_at": ended_at,
                "duration_mins": duration_mins,
                "stats": {
                    "total":   len(group),
                    "applied": applied,
                    "skipped": skipped,
                    "errors":  errors,
                    "manual":  manual,
                    "avg_score": avg_sc,
                },
                "platforms": platforms,
                "log_file": log_meta.get("log_file"),
                "log_size_kb": log_meta.get("log_size_kb"),
                "applications": apps_clean,
            })

        # Sort by date descending
        runs.sort(key=lambda r: r["date"], reverse=True)
        return {"runs": runs, "total_runs": len(runs)}

    except Exception as e:
        logger.error(f"[API] /api/runs error: {e}", exc_info=True)
        return {"runs": [], "error": str(e)}

@app.get("/api/history")
def get_history(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    platform: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    df = load_csv()
    if df.empty:
        return {"items": [], "total": 0, "page": page, "per_page": per_page}

    try:
        if platform:
            platform_col = "Platform" if "Platform" in df.columns else "Source" if "Source" in df.columns else None
            if platform_col:
                df = df[df[platform_col].astype(str).str.lower() == platform.lower()]

        if status and "Status" in df.columns:
            df = df[df["Status"].astype(str).str.lower() == status.lower()]

        if date_from and "Date" in df.columns:
            df = df[df["Date"] >= date_from]

        if date_to and "Date" in df.columns:
            df = df[df["Date"] <= date_to]

        total = len(df)
        df = df.iloc[::-1]
        start = (page - 1) * per_page
        end = start + per_page
        items = clean_dataframe_for_json(df.iloc[start:end]).to_dict(orient="records")

        return {
            "items": items,
            "total": int(total),
            "page": int(page),
            "per_page": int(per_page),
            "total_pages": int((total + per_page - 1) // per_page),
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/logs")
def get_logs(lines: int = Query(100, ge=10, le=2000)):
    latest_log = get_latest_log_file()
    if not latest_log:
        return {"logs": ["No logs found."], "file": None}

    try:
        with open(latest_log, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()[-lines:]
            return {"logs": [line.rstrip("\n") for line in all_lines], "file": str(latest_log.name)}
    except Exception as e:
        return {"logs": [f"Error reading logs: {e}"], "file": None}

@app.get("/api/logs/stream")
async def stream_logs():
    async def event_generator():
        for _ in range(10):
            log_file = get_latest_log_file()
            if log_file:
                break
            await asyncio.sleep(0.5)
        else:
            yield "data: [Waiting for bot to start...]\n\n"
            return

        try:
            with open(log_file, "r", encoding="utf-8", errors="replace") as f:
                history = f.readlines()[-50:]
                for line in history:
                    yield f"data: {line.rstrip()}\n\n"
                while True:
                    line = f.readline()
                    if line:
                        yield f"data: {line.rstrip()}\n\n"
                    else:
                        await asyncio.sleep(1)
                        yield ": heartbeat\n\n"
        except Exception as e:
            yield f"data: [Stream error: {e}]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

@app.get("/api/session/live")
def get_session_live():
    return session_state

class SessionUpdate(BaseModel):
    status: str = "running"
    current_platform: str = ""
    current_listing: str = ""
    current_step: str = ""
    applied_count: int = 0
    skipped_count: int = 0
    error_count: int = 0
    event: Optional[dict] = None

@app.post("/api/session/update")
async def update_live_session(update: SessionUpdate):
    session_state["status"] = update.status
    session_state["current_platform"] = update.current_platform
    session_state["current_listing"] = update.current_listing
    session_state["current_step"] = update.current_step
    session_state["applied_count"] = update.applied_count
    session_state["skipped_count"] = update.skipped_count
    session_state["error_count"] = update.error_count

    if update.event:
        event = dict(update.event)
        if "timestamp" not in event:
            event["timestamp"] = datetime.utcnow().isoformat() + "Z"
        session_state["events"].append(event)
        if len(session_state["events"]) > 100:
            session_state["events"] = session_state["events"][-100:]

    if ws_clients:
        payload = json.dumps({"type": "session_state", "data": session_state})
        dead = []
        for ws in ws_clients:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            if ws in ws_clients:
                ws_clients.remove(ws)
    return {"ok": True}

@app.websocket("/ws/live")
async def websocket_live(websocket: WebSocket):
    await websocket.accept()
    ws_clients.append(websocket)
    try:
        await websocket.send_text(json.dumps({"type": "session_state", "data": session_state}))
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                await websocket.send_text(json.dumps({"type": "ping"}))
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        if websocket in ws_clients:
            ws_clients.remove(websocket)

@app.get("/api/session/key", dependencies=[Depends(verify_api_key)])
def get_session_key():
    return {"key": os.getenv("SESSION_SECRET_KEY", "")}

class SessionUploadRequest(BaseModel):
    platform: str
    encrypted_blob: list[int]
    iv: list[int]

@app.post("/api/session/upload", dependencies=[Depends(verify_api_key)])
def upload_session(req: SessionUploadRequest):
    try:
        key = get_aesgcm_key()
        aesgcm = AESGCM(key)
        ciphertext = bytes(req.encrypted_blob)
        iv = bytes(req.iv)
        plaintext = aesgcm.decrypt(iv, ciphertext, None)
        session_data = json.loads(plaintext.decode('utf-8'))
        
        if "cookies" not in session_data or "capturedAt" not in session_data:
            raise ValueError("Invalid session shape")
            
        iv_rest = os.urandom(12)
        ciphertext_rest = aesgcm.encrypt(iv_rest, json.dumps(session_data).encode('utf-8'), None)
        
        at_rest_data = {
            "capturedAt": session_data["capturedAt"],
            "platform": req.platform,
            "iv": list(iv_rest),
            "encrypted_blob": list(ciphertext_rest)
        }
            
        file_path = SESSION_DIR / f"{req.platform}_session.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(at_rest_data, f, indent=2)
            
        return {"status": "success", "message": f"Session captured for {req.platform}"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to decrypt/save session: {e}")

@app.get("/api/session/status")
def get_session_status():
    platforms = ["linkedin", "naukri", "internshala", "unstop"]
    status = {}
    for plat in platforms:
        file_path = SESSION_DIR / f"{plat}_session.json"
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                captured_dt = datetime.fromisoformat(data["capturedAt"].replace("Z", "+00:00"))
                age = (datetime.now().astimezone() - captured_dt).days
                status[plat] = {"connected": True, "capturedAt": data["capturedAt"], "stale": age > 7}
            except Exception:
                status[plat] = {"connected": False}
        else:
            status[plat] = {"connected": False}
    return status

@app.delete("/api/session/{platform}", dependencies=[Depends(verify_api_key)])
def delete_session(platform: str):
    file_path = SESSION_DIR / f"{platform}_session.json"
    if file_path.exists():
        try:
            file_path.unlink()
            return {"status": "success"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    return {"status": "not_found"}

@app.get("/api/schedule")
def get_schedule():
    config = load_schedule_config()
    return {
        "enabled": config["enabled"],
        "days": config["days"],
        "time": config["time"],
        "dry_run": config["dry_run"],
        "next_run": get_next_scheduled_run() if config["enabled"] else None,
    }

@app.post("/api/schedule", dependencies=[Depends(verify_api_key)])
def update_schedule(config: dict):
    config = validate_schedule_config(config)
    try:
        save_schedule_config(config)
        schedule_jobs_from_config(config)
        return {"message": "Schedule saved successfully", "schedule": config}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/status")
def get_status():
    global current_process, current_process_started_at
    # Sync session_state with actual process state
    actually_running = current_process is not None and current_process.poll() is None
    if not actually_running and session_state["status"] == "running":
        # Process died but session_state wasn't reset yet — fix it now
        session_state["status"] = "idle"
        session_state["current_platform"] = ""
    return {
        "is_running": actually_running,
        "status": session_state["status"],
        "pid": current_process.pid if current_process is not None and current_process.poll() is None else None,
        "started_at": current_process_started_at.isoformat() if current_process_started_at else None,
        "next_run": get_next_scheduled_run() if load_schedule_config().get("enabled", False) else None,
        "schedule_enabled": load_schedule_config().get("enabled", False),
    }

class RunBotRequest(BaseModel):
    dry_run: bool = False
    headless: bool = True

@app.post("/api/run-bot", dependencies=[Depends(verify_api_key)])
def run_bot(req: RunBotRequest = RunBotRequest()):
    spawned = spawn_bot_process(dry_run=req.dry_run, headless=req.headless)
    if not spawned:
        return {"status": "already_running", "message": "Bot is already running", "already_running": True}
    return {"status": "success", "message": "Bot started in background", "already_running": False}

@app.post("/api/start", dependencies=[Depends(verify_api_key)])
def start_bot(
    platform: Optional[str] = None,
    dry_run: Optional[bool] = None,
    headless: bool = False,
    run_now: bool = True,          # default True — dashboard always wants immediate run
):
    if dry_run is None:
        dry_run = False
    spawned = spawn_bot_process(dry_run=dry_run, headless=headless, platform=platform, run_now=run_now)
    if not spawned:
        return {"message": "Failed to queue bot run", "already_running": True}
    return {"message": "Bot queued", "already_running": False}

@app.post("/api/stop", dependencies=[Depends(verify_api_key)])
def stop_bot():
    stopped = stop_bot_process()
    if stopped:
        session_state["status"] = "idle"
        session_state["current_platform"] = ""
        session_state["events"].append({"timestamp": datetime.now().isoformat(), "type": "info", "message": "Bot stopped by user"})
        return {"message": "Bot stopped.", "stopped": True}
    return {"message": "No running bot to stop.", "stopped": False}

@app.post("/api/session/pause", dependencies=[Depends(verify_api_key)])
def pause_session():
    if session_state["status"] != "running":
        return {"message": "No active session to pause."}
    session_state["status"] = "paused"
    return {"message": "Session paused."}

@app.post("/api/session/resume", dependencies=[Depends(verify_api_key)])
def resume_session():
    if session_state["status"] != "paused":
        return {"message": "No paused session to resume."}
    session_state["status"] = "running"
    return {"message": "Session resumed."}

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "version": "2.0.0",
        "session": session_state["status"],
        "csv_exists": CSV_PATH.exists(),
        "logs_dir": str(LOGS_DIR),
        "timestamp": datetime.now().isoformat(),
    }

# ── History Endpoints ─────────────────────────────────────────────

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
def get_profile(session: Session = Depends(get_session)):
    from sqlmodel import select
    from core.models import User, UserProfile
    user = session.exec(select(User).order_by(User.id)).first()
    if not user:
        return {}
    profile = session.exec(select(UserProfile).where(UserProfile.user_id == user.id)).first()
    if not profile:
        return {}
    return profile.model_dump()

@app.post("/api/profile")
async def save_profile(data: dict, session: Session = Depends(get_session)):
    from sqlmodel import select
    from core.models import User, UserProfile
    try:
        user = session.exec(select(User).order_by(User.id)).first()
        if not user:
            user = User(email="admin@default.com", hashed_password="")
            session.add(user)
            session.commit()
            session.refresh(user)

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
async def parse_resume(file: UploadFile = File(...)):
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
            max_tokens=2000,
            response_format="json"
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
def get_settings(session: Session = Depends(get_session)):
    from core.models import SystemSettings
    # Load all keys from DB
    db_settings = session.exec(select(SystemSettings)).all()
    settings_dict = {s.key: s.value for s in db_settings}
    
    # Also include os.environ for keys that are set in Render (so UI shows them)
    for k, v in os.environ.items():
        if k in ["GROQ_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY", "WHATSAPP_PHONE", "WHATSAPP_API_KEY", "DATABASE_URL"]:
            if k not in settings_dict:
                settings_dict[k] = v
                
    return settings_dict

@app.post("/api/settings")
def save_settings(data: dict, session: Session = Depends(get_session)):
    from core.models import SystemSettings
    import os
    try:
        for k, v in data.items():
            setting = session.exec(select(SystemSettings).where(SystemSettings.key == k)).first()
            if setting:
                setting.value = str(v)
                session.add(setting)
            else:
                setting = SystemSettings(key=k, value=str(v))
                session.add(setting)
            
            # Immediately update process environment so os.getenv sees it
            os.environ[k] = str(v)
        
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

