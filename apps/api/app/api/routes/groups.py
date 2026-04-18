from __future__ import annotations

import logging
import secrets
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, nullslast, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.enums import MembershipStatus, RoleCode
from app.db.models import AccessCode, AccessGroup, AppUser, GroupMembership, Workspace
from app.db.session import SessionLocal, get_db
from app.schemas.api import AccessCodeIssueRequest, GroupCreateRequest, MembershipGrantRequest, MembershipRoleUpdateRequest
from app.schemas.serializers import serialize_group_membership
from app.services.audit import log_audit_event
from app.services.authorization import authorize
from app.services.workflow import (
    create_group,
    grant_group_membership,
    hash_access_code,
    revoke_group_membership,
    update_group_membership_role,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["groups"])


@router.get("/groups")
def list_groups(current_user: AppUser = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict]:
    roles = authorize(session=db, user=current_user, required_roles=[])

    latest_ws = (
        select(Workspace.access_group_id, func.max(Workspace.updated_at).label("last_activity_at"))
        .group_by(Workspace.access_group_id)
        .subquery("latest_ws")
    )

    q = (
        select(AccessGroup, latest_ws.c.last_activity_at)
        .outerjoin(latest_ws, latest_ws.c.access_group_id == AccessGroup.access_group_id)
    )
    if "admin" not in roles:
        q = q.join(GroupMembership, GroupMembership.access_group_id == AccessGroup.access_group_id).where(
            GroupMembership.app_user_id == current_user.app_user_id,
            GroupMembership.membership_status == MembershipStatus.ACTIVE,
        )
    q = q.order_by(nullslast(latest_ws.c.last_activity_at.desc()))

    rows = db.execute(q).all()
    return [
        {
            "access_group_id": str(group.access_group_id),
            "group_name": group.group_name,
            "group_description": group.group_description,
            "group_status": group.group_status.value,
            "last_activity_at": last_activity_at.isoformat() if last_activity_at else None,
        }
        for group, last_activity_at in rows
    ]


@router.post("/groups", status_code=status.HTTP_201_CREATED)
def create_group_route(
    payload: GroupCreateRequest,
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    authorize(session=db, user=current_user, required_roles=[])
    try:
        group = create_group(db, actor=current_user, payload=payload)
    except HTTPException:
        db.commit()
        raise
    try:
        db.commit()
    except Exception:
        db.rollback()
        # Log commit failure in an emergency session to preserve auditability
        logger.exception("Group creation commit failed for group_name=%s", payload.group_name)
        try:
            with SessionLocal() as emergency_session:
                log_audit_event(
                    emergency_session,
                    event_type="group_creation_commit_failed",
                    entity_type="access_group",
                    entity_id=None,
                    actor_user=None,
                    payload={"group_name": payload.group_name, "actor_user_id": str(current_user.app_user_id)},
                )
                emergency_session.commit()
        except Exception:
            logger.exception("Emergency audit log also failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Group creation failed. The attempt has been recorded.",
        )
    return {
        "access_group_id": str(group.access_group_id),
        "group_name": group.group_name,
        "group_description": group.group_description,
        "group_status": group.group_status.value,
    }


@router.get("/groups/{group_id}")
def get_group(
    group_id: UUID,
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    authorize(session=db, user=current_user, required_roles=[], access_group_id=group_id)
    group = db.get(AccessGroup, group_id)
    if group is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found.")
    active_count = db.scalar(
        select(func.count(GroupMembership.group_membership_id)).where(
            GroupMembership.access_group_id == group_id,
            GroupMembership.membership_status == MembershipStatus.ACTIVE,
        )
    )
    return {
        "access_group_id": str(group.access_group_id),
        "group_name": group.group_name,
        "group_description": group.group_description,
        "group_status": group.group_status.value,
        "active_membership_count": active_count or 0,
    }


@router.get("/groups/{group_id}/workspaces")
def list_group_workspaces(
    group_id: UUID,
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    authorize(session=db, user=current_user, required_roles=[], access_group_id=group_id)
    workspaces = db.scalars(
        select(Workspace)
        .where(Workspace.access_group_id == group_id)
        .order_by(Workspace.updated_at.desc())
    ).all()
    return [
        {
            "workspace_id": str(w.workspace_id),
            "workspace_title": w.workspace_title,
            "business_date": w.business_date.isoformat() if w.business_date else None,
            "workspace_status": w.workspace_status.value,
            "updated_at": w.updated_at.isoformat(),
        }
        for w in workspaces
    ]


@router.post("/access-codes", status_code=status.HTTP_201_CREATED)
def issue_access_code(
    payload: AccessCodeIssueRequest,
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    authorize(session=db, user=current_user, required_roles=[RoleCode.ADMIN])
    raw_code = secrets.token_urlsafe(8)
    code = AccessCode(
        code_value_hash=hash_access_code(raw_code),
        issued_by_user_id=current_user.app_user_id,
        issued_for_scope=payload.issued_for_scope,
        max_uses=payload.max_uses,
        expires_at=payload.expires_at,
    )
    db.add(code)
    db.commit()
    return {
        "access_code_id": str(code.access_code_id),
        "plain_code": raw_code,
        "max_uses": code.max_uses,
        "expires_at": code.expires_at.isoformat() if code.expires_at else None,
    }


@router.get("/groups/{group_id}/memberships")
def list_group_memberships(
    group_id: UUID,
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    authorize(session=db, user=current_user, required_roles=[], access_group_id=group_id)
    memberships = db.scalars(
        select(GroupMembership)
        .where(GroupMembership.access_group_id == group_id)
        .order_by(GroupMembership.granted_at.desc())
    ).all()
    return [serialize_group_membership(membership) for membership in memberships]


@router.post("/groups/{group_id}/memberships", status_code=status.HTTP_201_CREATED)
def create_group_membership_route(
    group_id: UUID,
    payload: MembershipGrantRequest,
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    authorize(session=db, user=current_user, required_roles=[RoleCode.ADMIN, RoleCode.GROUP_ADMIN], access_group_id=group_id)
    membership = grant_group_membership(db, actor=current_user, group_id=group_id, payload=payload)
    db.commit()
    return serialize_group_membership(membership)


@router.delete("/groups/{group_id}/memberships/{membership_id}")
def revoke_group_membership_route(
    group_id: UUID,
    membership_id: UUID,
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    authorize(session=db, user=current_user, required_roles=[RoleCode.ADMIN, RoleCode.GROUP_ADMIN], access_group_id=group_id)
    membership = db.get(GroupMembership, membership_id)
    if membership is None or membership.access_group_id != group_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membership not found.")
    revoke_group_membership(db, actor=current_user, membership=membership)
    db.commit()
    return serialize_group_membership(membership)


@router.post("/groups/{group_id}/memberships/{membership_id}/role")
def update_group_membership_role_route(
    group_id: UUID,
    membership_id: UUID,
    payload: MembershipRoleUpdateRequest,
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    authorize(session=db, user=current_user, required_roles=[RoleCode.ADMIN, RoleCode.GROUP_ADMIN], access_group_id=group_id)
    membership = db.get(GroupMembership, membership_id)
    if membership is None or membership.access_group_id != group_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membership not found.")
    membership = update_group_membership_role(db, actor=current_user, membership=membership, payload=payload)
    db.commit()
    return serialize_group_membership(membership)
