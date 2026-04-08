from __future__ import annotations

import secrets
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.security import create_session_token, verify_password
from app.db.enums import AuthType
from app.db.models import AppUser, AuthIdentity, CompanyPerson
from app.services.audit import log_audit_event


def _verify_password_identity(session: Session, *, username: str, password: str) -> AuthIdentity:
    identity = session.scalar(
        select(AuthIdentity)
        .options(joinedload(AuthIdentity.app_user).joinedload(AppUser.company_person))
        .where(
            AuthIdentity.username == username,
            AuthIdentity.auth_type == AuthType.USERNAME_PASSWORD,
            AuthIdentity.disabled_at.is_(None),
        )
    )
    if identity is None or identity.password_hash is None or not verify_password(password, identity.password_hash):
        log_audit_event(
            session,
            event_type="login_failed",
            entity_type="auth_identity",
            entity_id=identity.auth_identity_id if identity else None,
            actor_user=identity.app_user if identity else None,
            payload={"username": username},
        )
        session.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")

    user = identity.app_user
    if not user.is_enabled or user.is_locked:
        log_audit_event(
            session,
            event_type="login_failed",
            entity_type="app_user",
            entity_id=user.app_user_id,
            actor_user=user,
            payload={"reason": "disabled_or_locked"},
        )
        session.commit()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is disabled or locked.")

    return identity


def authenticate_password(session: Session, *, username: str, password: str) -> tuple[AppUser, str]:
    identity = _verify_password_identity(session, username=username, password=password)
    user = identity.app_user

    identity.last_used_at = user.last_login_at = datetime.now(UTC)
    token = create_session_token(user.app_user_id)
    log_audit_event(
        session,
        event_type="login_succeeded",
        entity_type="app_user",
        entity_id=user.app_user_id,
        actor_user=user,
        payload={"username": username},
    )
    session.commit()
    session.refresh(user)
    return user, token


def start_sso_login(*, provider: str) -> dict[str, str]:
    state = secrets.token_urlsafe(24)
    return {
        "provider": provider,
        "state": state,
        "authorization_url": f"/auth/login/sso/callback?provider={provider}&state={state}",
        "mode": "stub",
    }


def authenticate_sso_stub(
    session: Session,
    *,
    provider: str,
    external_subject: str,
    email: str,
) -> dict:
    identity = session.scalar(
        select(AuthIdentity)
        .options(joinedload(AuthIdentity.app_user).joinedload(AppUser.company_person))
        .where(
            AuthIdentity.external_subject == external_subject,
            AuthIdentity.auth_type == AuthType.SSO,
            AuthIdentity.disabled_at.is_(None),
        )
    )
    if identity is not None:
        user = identity.app_user
        if not user.is_enabled or user.is_locked:
            log_audit_event(
                session,
                event_type="login_failed",
                entity_type="app_user",
                entity_id=user.app_user_id,
                actor_user=user,
                payload={"reason": "disabled_or_locked", "provider": provider},
            )
            session.commit()
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is disabled or locked.")

        identity.last_used_at = user.last_login_at = datetime.now(UTC)
        token = create_session_token(user.app_user_id)
        log_audit_event(
            session,
            event_type="login_succeeded",
            entity_type="app_user",
            entity_id=user.app_user_id,
            actor_user=user,
            payload={"provider": provider, "auth_type": AuthType.SSO.value},
        )
        session.commit()
        session.refresh(user)
        return {"login_state": "linked", "user": user, "session_token": token}

    person = session.scalar(select(CompanyPerson).where(CompanyPerson.email == email))
    if person is None:
        log_audit_event(
            session,
            event_type="unknown_identity",
            entity_type="auth_identity",
            entity_id=None,
            actor_user=None,
            payload={"provider": provider, "external_subject": external_subject, "email": email},
        )
        session.commit()
        return {"login_state": "unknown_identity", "email": email}

    user = session.scalar(
        select(AppUser)
        .options(joinedload(AppUser.company_person))
        .where(AppUser.company_person_id == person.company_person_id)
    )
    log_audit_event(
        session,
        event_type="identity_linking_required",
        entity_type="company_person",
        entity_id=person.company_person_id,
        actor_user=user,
        payload={"provider": provider, "external_subject": external_subject, "email": email},
    )
    session.commit()
    return {"login_state": "identity_linking_required", "person": person, "user": user}


def link_sso_identity(
    session: Session,
    *,
    provider: str,
    username: str,
    password: str,
    external_subject: str,
    email: str,
) -> tuple[AppUser, str]:
    identity = _verify_password_identity(session, username=username, password=password)
    user = identity.app_user
    if user.company_person.email.lower() != email.lower():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email does not match the authenticated user.")

    existing = session.scalar(
        select(AuthIdentity).where(
            AuthIdentity.external_subject == external_subject,
            AuthIdentity.auth_type == AuthType.SSO,
            AuthIdentity.disabled_at.is_(None),
        )
    )
    if existing is not None and existing.app_user_id != user.app_user_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="SSO identity is already linked.")

    if existing is None:
        session.add(
            AuthIdentity(
                app_user_id=user.app_user_id,
                auth_type=AuthType.SSO,
                external_subject=external_subject,
                is_primary=False,
                is_verified=True,
            )
        )
        log_audit_event(
            session,
            event_type="identity_linked",
            entity_type="auth_identity",
            entity_id=None,
            actor_user=user,
            payload={"provider": provider, "external_subject": external_subject, "email": email},
        )
    token = create_session_token(user.app_user_id)
    identity.last_used_at = user.last_login_at = datetime.now(UTC)
    log_audit_event(
        session,
        event_type="login_succeeded",
        entity_type="app_user",
        entity_id=user.app_user_id,
        actor_user=user,
        payload={"provider": provider, "auth_type": AuthType.SSO.value, "linked_during_login": True},
    )
    session.commit()
    session.refresh(user)
    return user, token
