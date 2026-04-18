from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.db.models import AppUser
from app.db.session import get_db
from app.schemas.api import (
    IdentityLinkRequest,
    LoginPasswordRequest,
    PreferencesUpdateRequest,
    SsoLoginCallbackRequest,
    SsoLoginStartRequest,
)
from app.schemas.serializers import serialize_user
from app.services.auth import authenticate_password, authenticate_sso_stub, link_sso_identity, start_sso_login
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


@router.get("/preferences")
def get_preferences(current_user: AppUser = Depends(get_current_user)) -> dict:
    return {"default_language": current_user.default_language.value}


@router.patch("/preferences")
def update_preferences(
    payload: PreferencesUpdateRequest,
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    current_user.default_language = payload.default_language
    db.commit()
    db.refresh(current_user)
    return {"default_language": current_user.default_language.value}


@router.post("/login/sso/start")
def login_sso_start(payload: SsoLoginStartRequest) -> dict[str, str]:
    return start_sso_login(provider=payload.provider)


@router.post("/login/sso/callback")
def login_sso_callback(
    payload: SsoLoginCallbackRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> dict:
    result = authenticate_sso_stub(
        db,
        provider=payload.provider,
        external_subject=payload.external_subject,
        email=payload.email,
    )
    if result["login_state"] == "linked":
        settings = get_settings()
        response.set_cookie(
            key=settings.session_cookie_name,
            value=result["session_token"],
            httponly=True,
            max_age=settings.session_max_age_seconds,
            samesite="lax",
        )
        roles = [role.value for role, _, _ in get_user_roles(db, user_id=result["user"].app_user_id)]
        body = serialize_user(result["user"], roles, result["session_token"])
        body["login_state"] = "linked"
        return body
    if result["login_state"] == "identity_linking_required":
        response.status_code = status.HTTP_202_ACCEPTED
        person = result["person"]
        return {
            "login_state": "identity_linking_required",
            "company_person_id": str(person.company_person_id),
            "employee_number": person.employee_number,
            "full_name_he": person.full_name_he,
            "full_name_en": person.full_name_en,
            "email": person.email,
        }
    response.status_code = status.HTTP_404_NOT_FOUND
    return {"login_state": "unknown_identity", "email": result["email"]}


@router.post("/identity-linking/complete")
def complete_identity_linking(
    payload: IdentityLinkRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> dict:
    user, token = link_sso_identity(
        db,
        provider=payload.provider,
        username=payload.username,
        password=payload.password,
        external_subject=payload.external_subject,
        email=payload.email,
    )
    settings = get_settings()
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        httponly=True,
        max_age=settings.session_max_age_seconds,
        samesite="lax",
    )
    roles = [role.value for role, _, _ in get_user_roles(db, user_id=user.app_user_id)]
    body = serialize_user(user, roles, token)
    body["login_state"] = "linked"
    return body


@router.post("/logout")
def logout(response: Response) -> dict[str, str]:
    response.delete_cookie(get_settings().session_cookie_name)
    return {"status": "ok"}
