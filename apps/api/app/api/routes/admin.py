from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.db.enums import RoleCode, ScopeType
from app.db.models import AppUser, AuditEvent, Role, UserRoleAssignment
from app.db.session import get_db
from app.schemas.api import RoleGrantRequest, UserPatchRequest
from app.schemas.serializers import serialize_audit_event
from app.services.audit import log_audit_event
from app.services.authorization import authorize, get_user_roles

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/audit-events")
def list_audit_events(
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    authorize(session=db, user=current_user, required_roles=[RoleCode.ADMIN])
    events = db.scalars(select(AuditEvent).order_by(AuditEvent.created_at.desc())).all()
    return [serialize_audit_event(event) for event in events]


@router.get("/users")
def list_users(
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    authorize(session=db, user=current_user, required_roles=[RoleCode.ADMIN, RoleCode.GROUP_ADMIN])
    users = db.scalars(select(AppUser).options(selectinload(AppUser.company_person)).order_by(AppUser.created_at)).all()
    results = []
    for user in users:
        roles = [role.value for role, _, _ in get_user_roles(db, user_id=user.app_user_id)]
        results.append(
            {
                "app_user_id": str(user.app_user_id),
                "employee_number": user.company_person.employee_number,
                "full_name_he": user.company_person.full_name_he,
                "full_name_en": user.company_person.full_name_en,
                "email": user.company_person.email,
                "roles": roles,
                "is_enabled": user.is_enabled,
                "is_locked": user.is_locked,
                "default_language": user.default_language.value,
            }
        )
    return results


@router.patch("/users/{user_id}", status_code=status.HTTP_200_OK)
def patch_user(
    user_id: UUID,
    payload: UserPatchRequest,
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    authorize(session=db, user=current_user, required_roles=[RoleCode.ADMIN])
    user = db.get(AppUser, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    if payload.is_enabled is not None:
        user.is_enabled = payload.is_enabled
    if payload.is_locked is not None:
        user.is_locked = payload.is_locked
    log_audit_event(
        db,
        event_type="user_patched",
        entity_type="app_user",
        entity_id=user.app_user_id,
        actor_user=current_user,
        payload={"is_enabled": payload.is_enabled, "is_locked": payload.is_locked},
    )
    db.commit()
    return {
        "app_user_id": str(user.app_user_id),
        "is_enabled": user.is_enabled,
        "is_locked": user.is_locked,
    }


@router.post("/users/{user_id}/roles", status_code=status.HTTP_201_CREATED)
def grant_user_role(
    user_id: UUID,
    payload: RoleGrantRequest,
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    authorize(session=db, user=current_user, required_roles=[RoleCode.ADMIN])
    user = db.get(AppUser, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    role = db.scalar(select(Role).where(Role.role_code == payload.role_code))
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found.")
    # Prevent duplicate active assignment
    existing = db.scalar(
        select(UserRoleAssignment).where(
            UserRoleAssignment.app_user_id == user_id,
            UserRoleAssignment.role_id == role.role_id,
            UserRoleAssignment.scope_type == payload.scope_type,
            UserRoleAssignment.scope_id == payload.scope_id,
            UserRoleAssignment.revoked_at.is_(None),
        )
    )
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Role already granted.")
    assignment = UserRoleAssignment(
        app_user_id=user_id,
        role_id=role.role_id,
        scope_type=payload.scope_type,
        scope_id=payload.scope_id,
        granted_by_user_id=current_user.app_user_id,
    )
    db.add(assignment)
    log_audit_event(
        db,
        event_type="role_granted",
        entity_type="user_role_assignment",
        entity_id=assignment.user_role_assignment_id,
        actor_user=current_user,
        payload={"target_user_id": str(user_id), "role_code": payload.role_code.value},
    )
    db.commit()
    return {
        "user_role_assignment_id": str(assignment.user_role_assignment_id),
        "app_user_id": str(assignment.app_user_id),
        "role_code": payload.role_code.value,
        "scope_type": assignment.scope_type.value,
        "scope_id": str(assignment.scope_id) if assignment.scope_id else None,
    }


@router.delete("/users/{user_id}/roles/{role_code}", status_code=status.HTTP_200_OK)
def revoke_user_role(
    user_id: UUID,
    role_code: RoleCode,
    scope_type: ScopeType = ScopeType.GLOBAL,
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    authorize(session=db, user=current_user, required_roles=[RoleCode.ADMIN])
    assignment = db.scalar(
        select(UserRoleAssignment)
        .join(Role, Role.role_id == UserRoleAssignment.role_id)
        .where(
            UserRoleAssignment.app_user_id == user_id,
            Role.role_code == role_code,
            UserRoleAssignment.scope_type == scope_type,
            UserRoleAssignment.revoked_at.is_(None),
        )
    )
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active role assignment not found.")
    assignment.revoked_at = datetime.now(UTC)
    assignment.revoked_by_user_id = current_user.app_user_id
    log_audit_event(
        db,
        event_type="role_revoked",
        entity_type="user_role_assignment",
        entity_id=assignment.user_role_assignment_id,
        actor_user=current_user,
        payload={"target_user_id": str(user_id), "role_code": role_code.value},
    )
    db.commit()
    return {"user_role_assignment_id": str(assignment.user_role_assignment_id), "revoked": True}
