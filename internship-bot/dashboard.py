import os
import sys
import time
import subprocess
import asyncio
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException
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
    """Lightweight summary: total applied and per-platform breakdown."""
    df = load_data()

    if df.empty:
        return {"total_applied": 0, "platforms": {}, "recent": []}

    applied_df = df[df["Status"].str.contains("Applied|Success", case=False, na=False)]

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
        "platforms": platforms,
        "recent": recent,
    }


# ──────────────────────────────────────────────────────────────
# /api/logs  — last 100 lines (polled)
# /api/logs/stream — Server-Sent Events live tail
# ──────────────────────────────────────────────────────────────

@app.get("/api/logs")
def get_logs():
    """Return the last 100 lines of the most recent run log."""
    latest = get_latest_log_file()
    if not latest:
        return {"logs": ["No logs found. Run the bot first."]}

    try:
        with open(latest, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()[-100:]
        return {"logs": [l.rstrip("\n") for l in lines]}
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
    global _bot_process
    is_running = _bot_process is not None and _bot_process.poll() is None
    return {"running": is_running}


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
    global _bot_process

    if _bot_process is not None and _bot_process.poll() is None:
        return {"message": "Bot is already running."}

    _bot_process = _spawn_bot(["python", "main.py", "--run-now"], headless=False)
    return {"message": "Bot started in the background.", "pid": _bot_process.pid}


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
