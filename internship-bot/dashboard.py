import os
import sys
import time
import subprocess
import asyncio
import json
from datetime import datetime, date
from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

app = FastAPI(title="ApplyFlow Dashboard API")

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

# Track the currently running bot process
_bot_process: subprocess.Popen | None = None
_bot_started_at: Optional[str] = None

# ── Live session state (written by the bot via /api/session/update) ────────────
_live_session: dict = {
    "status": "idle",
    "current_platform": "",
    "current_listing": "",
    "current_step": "",
    "applied_count": 0,
    "skipped_count": 0,
    "error_count": 0,
    "events": [],
}
_ws_clients: list[WebSocket] = []


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────

def load_data() -> pd.DataFrame:
    if not CSV_PATH.exists():
        return pd.DataFrame()

    try:
        df = pd.read_csv(CSV_PATH)
        expected_cols = ["Date", "Company", "Role", "Location", "Source",
                         "Status", "Score", "Apply URL", "Cover Note Preview"]
        for col in expected_cols:
            if col not in df.columns:
                df[col] = ""
        df = df.sort_values(by="Date", ascending=False).reset_index(drop=True)
        return df
    except Exception as e:
        print(f"Error loading data: {e}")
        return pd.DataFrame()


def get_latest_log_file() -> Path | None:
    log_files = list(LOGS_DIR.glob("run_*.log"))
    if not log_files:
        return None
    return max(log_files, key=os.path.getctime)


def _spawn_bot(cmd: list[str], headless: bool) -> subprocess.Popen:
    """
    Spawn the bot subprocess.
    - headless=False → Chrome opens visibly on screen (CREATE_NEW_CONSOLE on Windows).
    - headless=True  → silent background process.
    """
    env = os.environ.copy()
    env["HEADLESS"] = "false" if not headless else "true"

    kwargs: dict = {"cwd": str(BASE_DIR), "env": env}

    if not headless and sys.platform == "win32":
        # CREATE_NEW_CONSOLE (0x10) gives the subprocess its own console window
        # and ensures Chrome's window is shown on the desktop.
        kwargs["creationflags"] = subprocess.CREATE_NEW_CONSOLE

    return subprocess.Popen(cmd, **kwargs)


# ──────────────────────────────────────────────────────────────
# /api/applications  — full application list + metrics
# ──────────────────────────────────────────────────────────────

@app.get("/api/applications")
def get_applications():
    """Returns all applications and aggregated metrics."""
    df = load_data()

    empty_response = {
        "metrics": {
            "total": 0, "applied": 0, "failed": 0,
            "manual": 0, "skipped": 0, "average_score": 0.0
        },
        "applications": []
    }

    if df.empty:
        return empty_response

    scores = pd.to_numeric(df["Score"], errors="coerce")
    avg_score = float(scores.mean()) if not scores.isna().all() else 0.0

    metrics = {
        "total": len(df),
        "applied": int(df["Status"].str.contains("Applied|Success", case=False, na=False).sum()),
        "failed": int(df["Status"].str.contains("Error|Failed", case=False, na=False).sum()),
        "manual": int(df["Status"].str.contains("Manual|Pending", case=False, na=False).sum()),
        "skipped": int(df["Status"].str.contains("Skipped|Dry Run", case=False, na=False).sum()),
        "average_score": round(avg_score, 1),
    }

    applications = df.where(pd.notnull(df), None).to_dict(orient="records")
    return {"metrics": metrics, "applications": applications}


# ──────────────────────────────────────────────────────────────
# /api/stats  — lightweight summary for stat cards
# ──────────────────────────────────────────────────────────────

@app.get("/api/stats")
def get_stats():
    """Lightweight summary: total applied, today's count, success rate, and per-platform breakdown."""
    df = load_data()

    if df.empty:
        return {
            "total_applied": 0,
            "today_applied": 0,
            "success_rate": 0,
            "platforms": {},
            "recent": [],
        }

    applied_mask = df["Status"].str.contains("Applied|Success", case=False, na=False)
    applied_df = df[applied_mask]

    # Today's applications
    today_str = date.today().strftime("%Y-%m-%d")
    today_applied = 0
    if "Date" in df.columns:
        today_applied = int(
            applied_df[applied_df["Date"].astype(str).str.startswith(today_str)].shape[0]
        )

    # Success rate = applied / total (excluding dry-runs)
    total = len(df)
    success_rate = round((len(applied_df) / total) * 100) if total > 0 else 0

    platforms = {}
    if "Source" in applied_df.columns:
        platforms = (
            applied_df["Source"]
            .str.strip()
            .str.title()
            .value_counts()
            .to_dict()
        )

    recent = df.head(5).where(pd.notnull(df.head(5)), None).to_dict(orient="records")

    return {
        "total_applied": len(applied_df),
        "today_applied": today_applied,
        "success_rate": success_rate,
        "platforms": platforms,
        "recent": recent,
    }


# ──────────────────────────────────────────────────────────────
# /api/logs  — last 100 lines (polled)
# /api/logs/stream — Server-Sent Events live tail
# ──────────────────────────────────────────────────────────────

@app.get("/api/logs")
def get_logs(lines: int = Query(default=100, ge=1, le=2000)):
    """Return the last N lines of the most recent run log (default 100, max 2000)."""
    latest = get_latest_log_file()
    if not latest:
        return {"logs": ["No logs found. Run the bot first."]}

    try:
        with open(latest, "r", encoding="utf-8", errors="replace") as f:
            raw_lines = f.readlines()[-lines:]
        return {"logs": [line.rstrip("\n") for line in raw_lines]}
    except Exception as e:
        return {"logs": [f"Error reading logs: {e}"]}


@app.get("/api/logs/stream")
async def stream_logs():
    """
    Server-Sent Events endpoint — streams new log lines in real time.
    The frontend connects with EventSource('/api/logs/stream') and receives
    'data: <line>\\n\\n' events as the bot writes to its log file.
    """
    async def event_generator():
        # Wait up to 5s for a log file to appear (bot may have just started)
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
                # Send last 50 lines as history first
                history = f.readlines()[-50:]
                for line in history:
                    yield f"data: {line.rstrip()}\n\n"

                # Then tail new lines
                while True:
                    line = f.readline()
                    if line:
                        yield f"data: {line.rstrip()}\n\n"
                    else:
                        # Heartbeat every 1s to keep connection alive
                        await asyncio.sleep(1)
                        yield ": heartbeat\n\n"
        except Exception as e:
            yield f"data: [Stream error: {e}]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # disable nginx buffering if proxied
        },
    )


# ──────────────────────────────────────────────────────────────
# /api/status — bot running check
# ──────────────────────────────────────────────────────────────

@app.get("/api/status")
def get_status():
    """Check if the bot process is currently running."""
    global _bot_process, _bot_started_at
    is_running = _bot_process is not None and _bot_process.poll() is None
    if not is_running:
        _bot_started_at = None  # clear start time when bot exits
    return {
        "is_running": is_running,
        "started_at": _bot_started_at,
        "schedule_enabled": False,
        "next_run": None,
    }


# ──────────────────────────────────────────────────────────────
# /api/run-bot  — trigger bot (frontend/App.tsx)
# /api/start    — trigger bot (dashboard/frontend)
# ──────────────────────────────────────────────────────────────

class RunBotRequest(BaseModel):
    dry_run: bool = False
    headless: bool = True   # False = Chrome opens visibly on screen


@app.post("/api/run-bot")
def run_bot(req: RunBotRequest = RunBotRequest()):
    """Trigger the bot to run in the background."""
    global _bot_process

    # Prevent double-start
    if _bot_process is not None and _bot_process.poll() is None:
        return {"status": "already_running", "message": "Bot is already running"}

    cmd = ["python", "main.py", "--run-now"]
    if req.dry_run:
        cmd.append("--dry-run")

    try:
        _bot_process = _spawn_bot(cmd, headless=req.headless)
        return {
            "status": "success",
            "message": "Bot started in background",
            "pid": _bot_process.pid,
            "headless": req.headless,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/start")
def start_bot():
    """Alias for /api/run-bot — for dashboard/frontend compatibility. Always shows browser."""
    global _bot_process, _bot_started_at

    if _bot_process is not None and _bot_process.poll() is None:
        # Bug 2 fix: include `already_running` field so the frontend alert fires
        return {"already_running": True, "message": "Bot is already running."}

    _bot_process = _spawn_bot(["python", "main.py", "--run-now"], headless=False)
    _bot_started_at = datetime.utcnow().isoformat() + "Z"
    return {"already_running": False, "message": "Bot started in the background.", "pid": _bot_process.pid}


# ──────────────────────────────────────────────────────────────
# /api/stop — stop the running bot process
# ──────────────────────────────────────────────────────────────

@app.post("/api/stop")
def stop_bot():
    """Terminate the running bot process."""
    global _bot_process, _bot_started_at
    if _bot_process is not None and _bot_process.poll() is None:
        _bot_process.terminate()
        _bot_started_at = None
        return {"message": "Bot stopped."}
    return {"message": "Bot was not running."}


# ──────────────────────────────────────────────────────────────
# /api/session/live — live session state (Bug 5 fix)
# /api/session/update — called by the bot to push updates
# ──────────────────────────────────────────────────────────────

@app.get("/api/session/live")
def get_live_session():
    """Return current live session state (polled by frontend every 2 s)."""
    global _bot_process
    is_running = _bot_process is not None and _bot_process.poll() is None
    session = dict(_live_session)
    if not is_running and session["status"] == "running":
        session["status"] = "idle"
    return session


class SessionUpdate(BaseModel):
    status: str = "running"
    current_platform: str = ""
    current_listing: str = ""
    current_step: str = ""
    applied_count: int = 0
    skipped_count: int = 0
    error_count: int = 0
    event: Optional[dict] = None  # single event to append


@app.post("/api/session/update")
async def update_live_session(update: SessionUpdate):
    """Bot calls this to push live session progress to the dashboard."""
    global _live_session
    _live_session["status"] = update.status
    _live_session["current_platform"] = update.current_platform
    _live_session["current_listing"] = update.current_listing
    _live_session["current_step"] = update.current_step
    _live_session["applied_count"] = update.applied_count
    _live_session["skipped_count"] = update.skipped_count
    _live_session["error_count"] = update.error_count

    if update.event:
        event = dict(update.event)
        if "timestamp" not in event:
            event["timestamp"] = datetime.utcnow().isoformat() + "Z"
        _live_session["events"] = (_live_session["events"] + [event])[-100:]

    # Broadcast to all connected WebSocket clients
    if _ws_clients:
        payload = json.dumps({"type": "session_state", "data": _live_session})
        dead = []
        for ws in _ws_clients:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            _ws_clients.remove(ws)

    return {"ok": True}


# ──────────────────────────────────────────────────────────────
# /ws/live — WebSocket for real-time events (Bug 5 fix)
# ──────────────────────────────────────────────────────────────

@app.websocket("/ws/live")
async def websocket_live(websocket: WebSocket):
    """WebSocket endpoint — sends session_state on connect, then on every update."""
    await websocket.accept()
    _ws_clients.append(websocket)
    try:
        # Send current state immediately on connect
        await websocket.send_text(
            json.dumps({"type": "session_state", "data": _live_session})
        )
        # Keep connection alive; data is pushed via update_live_session
        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=30)
            except asyncio.TimeoutError:
                # Send a heartbeat ping
                await websocket.send_text(json.dumps({"type": "ping"}))
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        if websocket in _ws_clients:
            _ws_clients.remove(websocket)


# ──────────────────────────────────────────────────────────────
# /api/schedule — read/write schedule config
# ──────────────────────────────────────────────────────────────

SCHEDULE_FILE = BASE_DIR / "data" / "schedule.json"
_DEFAULT_SCHEDULE = {"enabled": False, "days": ["mon", "tue", "wed", "thu", "fri"], "time": "09:00", "dry_run": True}


@app.get("/api/schedule")
def get_schedule():
    """Return current schedule config."""
    if SCHEDULE_FILE.exists():
        try:
            return json.loads(SCHEDULE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return _DEFAULT_SCHEDULE


@app.post("/api/schedule")
def save_schedule(config: dict):
    """Persist schedule config and return it."""
    SCHEDULE_FILE.parent.mkdir(parents=True, exist_ok=True)
    SCHEDULE_FILE.write_text(json.dumps(config, indent=2), encoding="utf-8")
    return {"schedule": config}


# ──────────────────────────────────────────────────────────────
# /api/health  — simple health check
# ──────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "csv_exists": CSV_PATH.exists(),
        "logs_dir": str(LOGS_DIR),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("dashboard:app", host="0.0.0.0", port=8000, reload=True)
