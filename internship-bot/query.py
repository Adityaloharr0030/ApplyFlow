from sqlmodel import create_engine, text, Session
engine = create_engine("postgresql://neondb_owner:npg_qL0mWCJV3UiS@ep-mute-violet-au9oj8hf.c-10.us-east-1.aws.neon.tech/neondb?sslmode=require")
with Session(engine) as session:
    res = session.exec(text("SELECT email, hashed_password FROM \"user\"")).fetchall()
    for row in res:
        print(row)
