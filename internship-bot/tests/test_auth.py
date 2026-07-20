import pytest
from fastapi.testclient import TestClient
from dashboard import app
from core.db import get_session
import core.models # Ensure models are loaded before SQLModel.metadata.create_all
from sqlmodel import SQLModel, Session, create_engine
import os

from sqlalchemy.pool import StaticPool

@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite:///:memory:", 
        connect_args={"check_same_thread": False}, 
        poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

def test_register_user(session: Session):
    app.dependency_overrides[get_session] = lambda: session
    response = client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "securepassword",
        "name": "Test User"
    })
    assert response.status_code == 200
    assert response.json() == {"message": "User registered successfully"}
    app.dependency_overrides.clear()

client = TestClient(app)
