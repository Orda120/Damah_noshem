from __future__ import annotations

from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.core.security import decode_session_token
from app.db.models import AppUser, UserRoleAssignment
from app.db.session import get_db


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
) -> AppUser:
    settings = get_settings()
    token = request.cookies.get(settings.session_cookie_name)
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1]
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")

    app_user_id: UUID | None = decode_session_token(token)
    if app_user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session.")

    user = db.scalar(
        select(AppUser)
        .options(
            joinedload(AppUser.company_person),
            joinedload(AppUser.role_assignments).joinedload(UserRoleAssignment.role),
        )
        .where(AppUser.app_user_id == app_user_id)
    )
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")
    return user
