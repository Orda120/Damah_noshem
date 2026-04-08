from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.db.models import AppUser
from app.db.session import get_db
from app.schemas.api import LoginPasswordRequest
from app.schemas.serializers import serialize_user
from app.services.auth import authenticate_password
from app.services.authorization import get_user_roles

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login/password")
def login_password(payload: LoginPasswordRequest, response: Response, db: Session = Depends(get_db)) -> dict:
    user, token = authenticate_password(db, username=payload.username, password=payload.password)
    settings = get_settings()
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        httponly=True,
        max_age=settings.session_max_age_seconds,
        samesite="lax",
    )
    roles = [role.value for role, _, _ in get_user_roles(db, user_id=user.app_user_id)]
    return serialize_user(user, roles, token)


@router.get("/me")
def me(current_user: AppUser = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    roles = [role.value for role, _, _ in get_user_roles(db, user_id=current_user.app_user_id)]
    return serialize_user(current_user, roles)


@router.post("/logout")
def logout(response: Response) -> dict[str, str]:
    response.delete_cookie(get_settings().session_cookie_name)
    return {"status": "ok"}
