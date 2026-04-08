from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.security import create_session_token, verify_password
from app.db.enums import AuthType
from app.db.models import AppUser, AuthIdentity
from app.services.audit import log_audit_event


def authenticate_password(session: Session, *, username: str, password: str) -> tuple[AppUser, str]:
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
