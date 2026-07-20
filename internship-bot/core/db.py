import os
from sqlmodel import SQLModel, create_engine, Session

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://neondb_owner:npg_qL0mWCJV3UiS@ep-mute-violet-au9oj8hf.c-10.us-east-1.aws.neon.tech/neondb?sslmode=require")
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)

def init_db():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
