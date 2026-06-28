from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import os
import subprocess
from pathlib import Path

app = FastAPI()

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

def get_latest_log_file():
    log_files = list(LOGS_DIR.glob("run_*.log"))
    if not log_files:
        return None
    return max(log_files, key=os.path.getctime)

@app.get("/api/stats")
def get_stats():
    if not CSV_FILE.exists():
        return {"total_applied": 0, "platforms": {}, "recent": []}
    
    try:
        df = pd.read_csv(CSV_FILE)
        platforms = df['Platform'].value_counts().to_dict()
        recent = df.tail(5).to_dict(orient="records")
        return {
            "total_applied": len(df),
            "platforms": platforms,
            "recent": recent[::-1]
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/applications")
def get_applications():
    if not CSV_FILE.exists():
        return []
    try:
        df = pd.read_csv(CSV_FILE)
        return df.to_dict(orient="records")[::-1]
    except Exception:
        return []

@app.get("/api/logs")
def get_logs():
    latest_log = get_latest_log_file()
    if not latest_log:
        return {"logs": ["No logs found."]}
    
    try:
        with open(latest_log, "r", encoding="utf-8") as f:
            # Return last 100 lines
            lines = f.readlines()[-100:]
            return {"logs": lines}
    except Exception as e:
        return {"logs": [f"Error reading logs: {e}"]}

@app.post("/api/start")
def start_bot(background_tasks: BackgroundTasks):
    def run_bot():
        # Start the bot as a subprocess in the base directory
        subprocess.run(["python", "main.py", "--run-now"], cwd=BASE_DIR)
        
    background_tasks.add_task(run_bot)
    return {"message": "Bot started in the background."}
