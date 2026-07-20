import traceback
from core.db import get_session
from core.models import RunEvent

def log_event(run_id: str, message: str, severity: str = "INFO", exc: Exception = None):
    try:
        tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)) if exc else None
        with next(get_session()) as session:
            event = RunEvent(
                run_id=run_id,
                severity=severity,
                message=message,
                traceback=tb
            )
            session.add(event)
            session.commit()
    except Exception as db_err:
        print(f"Failed to write log to DB: {db_err}")
