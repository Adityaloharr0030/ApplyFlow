"""
dashboard/backend/api.py
────────────────────────
ApplyFlow Dashboard API — FastAPI backend.

Like ApplyCove: "Real-time session monitor, application history,
schedule manager, and live activity feed."

Endpoints:
  GET  /api/stats           — Dashboard overview stats
  GET  /api/applications    — All applications (paginated, filterable)
  GET  /api/history         — Paginated application history with filters
  GET  /api/logs            — Latest run logs
  GET  /api/session/live    — Current session status
  GET  /api/schedule        — Get all schedules
  POST /api/schedule        — Update schedules
  POST /api/start           — Start bot in background
  POST /api/session/pause   — Pause current session
  POST /api/session/resume  — Resume paused session
  WS   /ws/live             — Real-time event stream
"""

from fastapi import FastAPI, BackgroundTasks, WebSocket, WebSocketDisconnect, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import os
import json
import re
import subprocess
import threading
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

app = FastAPI(title="ApplyFlow Dashboard API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).parent.parent.parent
LOGS_DIR = BASE_DIR / "logs"
CSV_FILE = LOGS_DIR / "applications.csv"
SCHEDULES_FILE = BASE_DIR / "data" / "schedules.json"
SCHEDULE_CONFIG_FILE = Path(__file__).parent / "schedule_config.json"
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
# Shared state for live session tracking

session_state = {
    "status": "idle",  # idle, running, paused
    "started_at": None,
    "current_platform": None,
    "current_listing": None,
    "current_step": None,
    "applied_count": 0,
    "skipped_count": 0,
    "error_count": 0,
    "last_event": None,
    "events": [],  # Rolling list of recent events (max 100)
}

# Connected WebSocket clients
ws_clients: list[WebSocket] = []


async def broadcast_event(event: dict):
    """Send an event to all connected WebSocket clients."""
    event["timestamp"] = datetime.now().isoformat()

    # Store in session state
    session_state["events"].append(event)
    if len(session_state["events"]) > 100:
        session_state["events"] = session_state["events"][-100:]
    session_state["last_event"] = event

    # Broadcast
    disconnected = []
    for ws in ws_clients:
        try:
            await ws.send_json(event)
        except Exception:
            disconnected.append(ws)

    for ws in disconnected:
        ws_clients.remove(ws)


def update_session(key: str, value):
    """Update session state."""
    session_state[key] = value


# ── Utility Functions ──────────────────────────────────────────────────────────

def get_latest_log_file():
    log_files = list(LOGS_DIR.glob("run_*.log"))
    if not log_files:
        return None
    return max(log_files, key=os.path.getctime)


def load_csv() -> pd.DataFrame:
    """Load applications CSV into a DataFrame."""
    if not CSV_FILE.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(CSV_FILE)
    except Exception:
        return pd.DataFrame()


def load_schedules() -> list:
    """Load schedules from JSON file."""
    try:
        if SCHEDULES_FILE.exists():
            with open(SCHEDULES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return []


def save_schedules(schedules: list):
    """Save schedules to JSON file."""
    try:
        SCHEDULES_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SCHEDULES_FILE, "w", encoding="utf-8") as f:
            json.dump(schedules, f, indent=2)
    except Exception as e:
        raise Exception(f"Failed to save schedules: {e}")

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


def clean_dataframe_for_json(df: pd.DataFrame) -> pd.DataFrame:
    """Replace NaN values and datetime types so JSON serialization succeeds."""
    df = df.copy()
    df = df.where(pd.notnull(df), None)
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].apply(lambda v: v.isoformat() if v is not None else None)
    return df


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


def get_schedule_status() -> dict:
    config = load_schedule_config()
    return {
        "enabled": config["enabled"],
        "days": config["days"],
        "time": config["time"],
        "dry_run": config["dry_run"],
        "next_run": get_next_scheduled_run() if config["enabled"] else None,
    }


def spawn_bot_process(dry_run: bool):
    global current_process, current_process_started_at
    with current_process_lock:
        if current_process is not None and current_process.poll() is None:
            return False

        cmd = ["python", "main.py", "--run-now"]
        if dry_run:
            cmd.append("--dry-run")

        env = os.environ.copy()
        env["DRY_RUN"] = "true" if dry_run else "false"

        current_process = subprocess.Popen(cmd, cwd=BASE_DIR, env=env)
        current_process_started_at = datetime.now()
        session_state["status"] = "running"
        session_state["started_at"] = current_process_started_at.isoformat()
        session_state["applied_count"] = 0
        session_state["skipped_count"] = 0
        session_state["error_count"] = 0
        session_state["current_listing"] = None
        session_state["current_step"] = None

        def wait_and_clear():
            global current_process, current_process_started_at
            if current_process is None:
                return
            try:
                current_process.wait()
            finally:
                with current_process_lock:
                    current_process = None
                    current_process_started_at = None
                    session_state["status"] = "idle"
                    session_state["current_listing"] = None
                    session_state["current_step"] = None

        thread = threading.Thread(target=wait_and_clear, daemon=True)
        thread.start()
        return True


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
        session_state["current_listing"] = None
        session_state["current_step"] = None
        return True


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
    spawned = spawn_bot_process(dry_run=config.get("dry_run", True))
    if spawned:
        print(f"[scheduler] Triggered scheduled bot run at {datetime.now().isoformat()}")
    else:
        print(f"[scheduler] Skipped scheduled bot run at {datetime.now().isoformat()} because another run is active")


@app.on_event("startup")
def startup_scheduler():
    config = load_schedule_config()
    if not SCHEDULE_CONFIG_FILE.exists():
        save_schedule_config(config)
    schedule_jobs_from_config(config)
    if not scheduler.running:
        scheduler.start()
    print(f"[api] Scheduler started; enabled={config.get('enabled')} next_run={get_next_scheduled_run()}")


# ── API Endpoints ──────────────────────────────────────────────────────────────

@app.get("/api/stats")
def get_stats():
    """Dashboard overview — total applied, platform breakdown, success rate, today's count."""
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
        # Platform breakdown
        platforms = {}
        if "Platform" in df.columns:
            platforms = {str(k): int(v) for k, v in df["Platform"].value_counts().to_dict().items()}
        elif "Source" in df.columns:
            platforms = {str(k): int(v) for k, v in df["Source"].value_counts().to_dict().items()}

        # Today's count
        today_applied = 0
        if "Date" in df.columns:
            today_str = datetime.now().strftime("%Y-%m-%d")
            today_applied = len(df[df["Date"].str.startswith(today_str, na=False)])

        # Success rate
        success_rate = 0
        if "Status" in df.columns:
            total = len(df)
            successes = len(df[df["Status"].str.lower().isin(["applied", "success", "submitted"])])
            success_rate = round((successes / total * 100) if total > 0 else 0, 1)

        # Recent applications
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
    """All applications, newest first."""
    df = load_csv()
    if df.empty:
        return []
    try:
        df = clean_dataframe_for_json(df)
        return df.to_dict(orient="records")[::-1]
    except Exception:
        return []


@app.get("/api/history")
def get_history(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    platform: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    """Paginated application history with filters."""
    df = load_csv()
    if df.empty:
        return {"items": [], "total": 0, "page": page, "per_page": per_page}

    try:
        # Apply filters
        if platform:
            platform_col = "Platform" if "Platform" in df.columns else "Source"
            if platform_col in df.columns:
                df = df[df[platform_col].str.lower() == platform.lower()]

        if status and "Status" in df.columns:
            df = df[df["Status"].str.lower() == status.lower()]

        if date_from and "Date" in df.columns:
            df = df[df["Date"] >= date_from]

        if date_to and "Date" in df.columns:
            df = df[df["Date"] <= date_to]

        total = len(df)

        # Paginate (newest first)
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
def get_logs(lines: int = Query(100, ge=10, le=500)):
    """Latest run log lines."""
    latest_log = get_latest_log_file()
    if not latest_log:
        return {"logs": ["No logs found."], "file": None}

    try:
        with open(latest_log, "r", encoding="utf-8") as f:
            all_lines = f.readlines()[-lines:]
            return {"logs": all_lines, "file": str(latest_log.name)}
    except Exception as e:
        return {"logs": [f"Error reading logs: {e}"], "file": None}


@app.get("/api/session/live")
def get_session_live():
    """Current session status — running/paused/idle, current listing, counts."""
    return session_state


@app.get("/api/schedule")
def get_schedule():
    """Get the current schedule config."""
    return get_schedule_status()


@app.post("/api/schedule")
def update_schedule(config: dict):
    """Update the persistent schedule config and reschedule jobs."""
    config = validate_schedule_config(config)
    try:
        save_schedule_config(config)
        schedule_jobs_from_config(config)
        return {"message": "Schedule saved successfully", "schedule": config}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/status")
def get_status():
    running = current_process is not None and current_process.poll() is None
    return {
        "is_running": running,
        "started_at": current_process_started_at.isoformat() if current_process_started_at else None,
        "next_run": get_next_scheduled_run() if load_schedule_config().get("enabled", False) else None,
        "schedule_enabled": load_schedule_config().get("enabled", False),
    }


@app.post("/api/start")
def start_bot(platform: Optional[str] = None, dry_run: Optional[bool] = None):
    """Start the bot in the background."""
    if current_process is not None and current_process.poll() is None:
        return {"message": "Already running", "already_running": True}

    # Manual starts should default to live mode unless explicitly overridden.
    if dry_run is None:
        dry_run = False

    spawned = spawn_bot_process(dry_run=dry_run)
    if not spawned:
        return {"message": "Already running", "already_running": True}
    return {"message": "Bot started", "already_running": False}


@app.post("/api/stop")
def stop_bot():
    """Stop a running bot process."""
    if stop_bot_process():
        return {"message": "Bot stopped", "stopped": True}
    return {"message": "No running process", "stopped": False}


@app.post("/api/session/pause")
def pause_session():
    """Pause the current session."""
    if session_state["status"] != "running":
        return {"message": "No active session to pause."}

    session_state["status"] = "paused"
    return {"message": "Session paused."}


@app.post("/api/session/resume")
def resume_session():
    """Resume a paused session."""
    if session_state["status"] != "paused":
        return {"message": "No paused session to resume."}

    session_state["status"] = "running"
    return {"message": "Session resumed."}


# ── WebSocket for Real-Time Events ─────────────────────────────────────────────

@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    """
    Real-time event stream.
    Events: application_submitted, application_skipped, application_error,
            otp_required, session_started, session_completed, etc.
    """
    await websocket.accept()
    ws_clients.append(websocket)

    # Send current state
    try:
        await websocket.send_json({
            "type": "session_state",
            "data": session_state,
            "timestamp": datetime.now().isoformat(),
        })
    except Exception:
        pass

    try:
        while True:
            # Keep connection alive, receive pings
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        if websocket in ws_clients:
            ws_clients.remove(websocket)
    except Exception:
        if websocket in ws_clients:
            ws_clients.remove(websocket)


# ── Health Check ───────────────────────────────────────────────────────────────

@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "version": "2.0.0",
        "session": session_state["status"],
        "timestamp": datetime.now().isoformat(),
    }
