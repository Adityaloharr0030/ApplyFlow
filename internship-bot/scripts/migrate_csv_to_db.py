import os
import sys
from pathlib import Path
import pandas as pd
from sqlmodel import Session, select
from datetime import datetime

# Ensure we can import from core
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.db import engine, init_db
from core.models import ApplicationLog, User

def migrate():
    print("Initializing DB...")
    init_db()

    csv_path = Path("logs/applications.csv")
    if not csv_path.exists():
        print(f"No CSV found at {csv_path}")
        return

    print("Loading CSV...")
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"Failed to read CSV: {e}")
        return

    print(f"Found {len(df)} rows in CSV.")

    with Session(engine) as session:
        # Get the first user (default user)
        user = session.exec(select(User)).first()
        if not user:
            print("No users found in database! Creating a default user...")
            from passlib.context import CryptContext
            pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
            hashed_password = pwd_context.hash("password")
            user = User(username="admin", email="admin@example.com", hashed_password=hashed_password)
            session.add(user)
            session.commit()
            session.refresh(user)
            print(f"Created default user (ID: {user.id})")

        print(f"Migrating applications for user ID {user.id}...")
        
        migrated_count = 0
        for idx, row in df.iterrows():
            # Parse row
            platform = str(row.get("Source", "unknown")).lower()
            apply_url = str(row.get("Apply URL", ""))
            
            # Simple deduplication based on URL
            if apply_url and apply_url.lower() != "nan":
                existing = session.exec(
                    select(ApplicationLog)
                    .where(ApplicationLog.user_id == user.id)
                    .where(ApplicationLog.platform == platform)
                    .where(ApplicationLog.apply_url == apply_url)
                ).first()
                if existing:
                    continue
            else:
                apply_url = ""
            
            title = str(row.get("Role", ""))
            if title.lower() == "nan": title = ""
            company = str(row.get("Company", ""))
            if company.lower() == "nan": company = ""
            location = str(row.get("Location", ""))
            if location.lower() == "nan": location = ""
            
            raw_score = row.get("Score")
            score = 0
            if pd.notna(raw_score):
                try:
                    score = int(float(raw_score))
                except:
                    pass
            
            status = str(row.get("Status", "")).lower()
            if status == "nan": status = ""
            is_dry_run = "dry run" in status or "skipped" in status
            
            raw_date = row.get("Date")
            applied_at = datetime.now().isoformat()
            if pd.notna(raw_date):
                try:
                    # CSV dates are often "YYYY-MM-DD HH:MM"
                    applied_at = pd.to_datetime(raw_date).isoformat()
                except:
                    pass

            app_log = ApplicationLog(
                user_id=user.id,
                platform=platform,
                apply_url=apply_url,
                title=title,
                company=company,
                location=location,
                score=score,
                status=status,
                dry_run=is_dry_run,
                applied_at=applied_at
            )
            session.add(app_log)
            migrated_count += 1
            
            # Commit in batches of 100
            if migrated_count % 100 == 0:
                session.commit()
                print(f"Migrated {migrated_count} applications...")
                
        # Final commit
        session.commit()
        print(f"Migration complete! Successfully migrated {migrated_count} new applications.")

if __name__ == "__main__":
    migrate()
