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

from fastapi import FastAPI, BackgroundTasks, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import os
import json
import subprocess
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

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
            platforms = df["Platform"].value_counts().to_dict()
        elif "Source" in df.columns:
            platforms = df["Source"].value_counts().to_dict()

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
        recent = df.tail(10).to_dict(orient="records")[::-1]

        return {
            "total_applied": len(df),
            "today_applied": today_applied,
            "platforms": platforms,
            "success_rate": success_rate,
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
        items = df.iloc[start:end].to_dict(orient="records")

        return {
            "items": items,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page,
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
    """Get all configured schedules."""
    return load_schedules()


@app.post("/api/schedule")
def update_schedule(schedules: list):
    """Update/replace all schedules."""
    try:
        save_schedules(schedules)
        return {"message": "Schedules updated successfully", "count": len(schedules)}
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/start")
def start_bot(background_tasks: BackgroundTasks, platform: Optional[str] = None):
    """Start the bot in the background."""
    if session_state["status"] == "running":
        return {"message": "Bot is already running."}

    def run_bot():
        session_state["status"] = "running"
        session_state["started_at"] = datetime.now().isoformat()
        session_state["applied_count"] = 0
        session_state["skipped_count"] = 0
        session_state["error_count"] = 0

        cmd = ["python", "main.py", "--run-now"]
        if platform:
            cmd.extend(["--platform", platform])

        try:
            subprocess.run(cmd, cwd=BASE_DIR)
        finally:
            session_state["status"] = "idle"
            session_state["current_listing"] = None
            session_state["current_step"] = None

    background_tasks.add_task(run_bot)
    return {"message": f"Bot started in the background{f' (platform: {platform})' if platform else ''}."}


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
