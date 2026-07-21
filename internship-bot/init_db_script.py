from core.db import init_db, engine
from sqlmodel import Session, select
from core.models import User
from core.auth import get_password_hash

init_db()

with Session(engine) as session:
    user = session.exec(select(User).where(User.email == "lohar6987@gmail.com")).first()
    if not user:
        user = User(email="lohar6987@gmail.com", hashed_password=get_password_hash("ApplyFlow@2024"))
        session.add(user)
        session.commit()
        print("User created!")
    else:
        user.hashed_password = get_password_hash("ApplyFlow@2024")
        session.add(user)
        session.commit()
        print("User updated!")
