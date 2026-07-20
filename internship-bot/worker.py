from dotenv import load_dotenv
load_dotenv()
import time
import logging
from sqlmodel import select
from core.db import get_session, engine
from core.models import JobQueue
from main import run_bot
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("worker")

def poll_jobs():
    logger.info("Worker started. Polling for jobs...")
    while True:
        try:
            with get_session() as session:
                # Find pending jobs
                statement = select(JobQueue).where(JobQueue.status == "pending").order_by(JobQueue.created_at)
                job = session.exec(statement).first()
                
                if job:
                    job.status = "running"
                    job.started_at = __import__("datetime").datetime.now().isoformat()
                    session.add(job)
                    session.commit()
                    
                    logger.info(f"Starting job {job.id} for platform {job.platform}")
                    
                    try:
                        # Call the bot logic directly
                        run_bot(
                            platform=job.platform if job.platform != "all" else None,
                            dry_run=job.dry_run,
                            headless=job.headless
                        )
                        job.status = "completed"
                    except Exception as e:
                        logger.error(f"Job {job.id} failed: {e}")
                        job.status = "failed"
                    
                    job.completed_at = __import__("datetime").datetime.now().isoformat()
                    session.add(job)
                    session.commit()
                    logger.info(f"Job {job.id} finished with status {job.status}")
                
        except Exception as e:
            logger.error(f"Error while polling: {e}")
            
        time.sleep(5)

if __name__ == "__main__":
    from core.db import init_db
    init_db()
    poll_jobs()
