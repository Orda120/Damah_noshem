from __future__ import annotations

import secrets
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.enums import MembershipStatus, RoleCode
from app.db.models import AccessCode, AccessGroup, AppUser, GroupMembership
from app.db.session import get_db
from app.schemas.api import AccessCodeIssueRequest, GroupCreateRequest, MembershipGrantRequest
from app.schemas.serializers import serialize_group_membership
from app.services.authorization import authorize
from app.services.workflow import create_group, grant_group_membership, hash_access_code, revoke_group_membership

router = APIRouter(tags=["groups"])


@router.get("/groups")
def list_groups(current_user: AppUser = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict]:
    roles = authorize(session=db, user=current_user, required_roles=[])
    if "admin" in roles:
        groups = db.scalars(select(AccessGroup).order_by(AccessGroup.group_name)).all()
    else:
        groups = db.scalars(
            select(AccessGroup)
            .join(GroupMembership, GroupMembership.access_group_id == AccessGroup.access_group_id)
            .where(
                GroupMembership.app_user_id == current_user.app_user_id,
                GroupMembership.membership_status == MembershipStatus.ACTIVE,
            )
            .order_by(AccessGroup.group_name)
        ).all()
    return [
        {
            "access_group_id": str(group.access_group_id),
            "group_name": group.group_name,
            "group_description": group.group_description,
            "group_status": group.group_status.value,
        }
        for group in groups
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
    db.commit()
    return {
        "access_group_id": str(group.access_group_id),
        "group_name": group.group_name,
        "group_description": group.group_description,
        "group_status": group.group_status.value,
    }


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
