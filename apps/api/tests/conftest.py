from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import close_all_sessions

os.environ["DATABASE_URL"] = "sqlite:///./tests/test.db"
os.environ["ARCHIVE_SCHEMA"] = ""
os.environ["ACCESS_POLICY_ENABLED"] = "false"
os.environ["JWT_SECRET"] = "test-secret"

from app.db.base import Base
from app.db.seed import main as seed_main
from app.db.session import SessionLocal, engine
from app.main import app


@pytest.fixture(autouse=True)
def reset_database():
    engine.dispose()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    seed_main()
    yield
    close_all_sessions()
    engine.dispose()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def login_as(client: TestClient, username: str, password: str) -> dict:
    response = client.post("/api/v1/auth/login/password", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return response.json()
