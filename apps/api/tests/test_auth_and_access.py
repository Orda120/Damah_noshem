from __future__ import annotations

from sqlalchemy import select

from app.db.models import AccessGroup, AuditEvent, GroupCreationEvent
from app.db.session import SessionLocal

from conftest import login_as


def test_password_login_success(client):
    payload = login_as(client, "admin", "admin123")
    assert payload["email"] == "admin@damah.local"
    assert "admin" in payload["roles"]


def test_password_login_failure_audited(client):
    response = client.post("/api/v1/auth/login/password", json={"username": "admin", "password": "wrong"})
    assert response.status_code == 401
    with SessionLocal() as session:
        failure = session.scalar(
            select(AuditEvent).where(AuditEvent.event_type == "login_failed").order_by(AuditEvent.created_at.desc())
        )
        assert failure is not None


def test_group_creation_failed_attempt_is_audited_and_does_not_create_group(client):
    login_as(client, "submitter", "submitter123")
    response = client.post(
        "/api/v1/groups",
        json={"group_name": "Bad Group", "group_description": "x", "access_code": "does-not-exist"},
    )
    assert response.status_code == 400
    with SessionLocal() as session:
        event = session.scalar(select(GroupCreationEvent).order_by(GroupCreationEvent.created_at.desc()))
        assert event is not None
        assert event.attempt_status.value == "failed"
        assert session.scalar(select(AccessGroup).where(AccessGroup.group_name == "Bad Group")) is None
