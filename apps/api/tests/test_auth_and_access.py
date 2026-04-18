from __future__ import annotations

from sqlalchemy import select

from app.db.enums import AuthType
from app.db.models import AccessGroup, AppUser, AuditEvent, AuthIdentity, CompanyPerson, GroupCreationEvent
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


def test_sso_stub_login_distinguishes_linked_identity(client):
    response = client.post(
        "/api/v1/auth/login/sso/callback",
        json={
            "provider": "stub",
            "external_subject": "stub-admin-subject",
            "email": "admin@damah.local",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["login_state"] == "linked"
    assert "admin" in body["roles"]


def test_sso_stub_login_requires_identity_linking_for_known_person(client):
    response = client.post(
        "/api/v1/auth/login/sso/callback",
        json={
            "provider": "stub",
            "external_subject": "stub-submitter-subject",
            "email": "submitter@damah.local",
        },
    )
    assert response.status_code == 202
    assert response.json()["login_state"] == "identity_linking_required"


def test_sso_stub_login_marks_unknown_identity(client):
    response = client.post(
        "/api/v1/auth/login/sso/callback",
        json={
            "provider": "stub",
            "external_subject": "stub-unknown-subject",
            "email": "missing@damah.local",
        },
    )
    assert response.status_code == 404
    assert response.json()["login_state"] == "unknown_identity"
    with SessionLocal() as session:
        event = session.scalar(
            select(AuditEvent).where(AuditEvent.event_type == "unknown_identity").order_by(AuditEvent.created_at.desc())
        )
        assert event is not None


def test_group_admin_membership_can_manage_group_without_global_group_admin_role(client):
    login_as(client, "submitter", "submitter123")
    response = client.post(
        "/api/v1/groups",
        json={"group_name": "Submitter Owned Group", "group_description": "x", "access_code": "seed-group-code"},
    )
    assert response.status_code == 201
    group_id = response.json()["access_group_id"]

    with SessionLocal() as session:
        reviewer = session.scalar(select(AppUser).join(CompanyPerson).where(CompanyPerson.email == "reviewer@damah.local"))
        reviewer_id = reviewer.app_user_id

    grant_response = client.post(
        f"/api/v1/groups/{group_id}/memberships",
        json={"app_user_id": str(reviewer_id), "membership_role": "member"},
    )
    assert grant_response.status_code == 201


def test_identity_linking_completion_creates_sso_identity(client):
    response = client.post(
        "/api/v1/auth/identity-linking/complete",
        json={
            "provider": "stub",
            "external_subject": "stub-submitter-subject",
            "email": "submitter@damah.local",
            "username": "submitter",
            "password": "submitter123",
        },
    )
    assert response.status_code == 200
    assert response.json()["login_state"] == "linked"
    with SessionLocal() as session:
        identity = session.scalar(
            select(AuthIdentity).where(
                AuthIdentity.external_subject == "stub-submitter-subject",
                AuthIdentity.auth_type == AuthType.SSO,
            )
        )
        assert identity is not None
