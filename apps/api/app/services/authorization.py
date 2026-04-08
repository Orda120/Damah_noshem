from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.enums import AccessDecisionType, MembershipStatus, ParticipantRole, RoleCode, ScopeType
from app.db.models import AccessPolicyDecision, AppUser, GroupMembership, UserRoleAssignment, WorkspaceParticipant
from app.services.audit import log_audit_event


def get_user_roles(session: Session, *, user_id: UUID) -> list[tuple[RoleCode, ScopeType, UUID | None]]:
    assignments = session.scalars(
        select(UserRoleAssignment).where(
            UserRoleAssignment.app_user_id == user_id,
            UserRoleAssignment.revoked_at.is_(None),
        )
    ).all()
    return [(assignment.role.role_code, assignment.scope_type, assignment.scope_id) for assignment in assignments]


def authorize(
    session: Session,
    *,
    user: AppUser,
    required_roles: list[RoleCode],
    access_group_id: UUID | None = None,
    workspace_id: UUID | None = None,
    participant_roles: list[ParticipantRole] | None = None,
) -> list[str]:
    settings = get_settings()
    if not user.is_enabled or user.is_locked:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is disabled or locked.")

    assignments = session.scalars(
        select(UserRoleAssignment).where(
            UserRoleAssignment.app_user_id == user.app_user_id,
            UserRoleAssignment.revoked_at.is_(None),
        )
    ).all()
    role_codes = [assignment.role.role_code for assignment in assignments]
    if required_roles and not any(role in role_codes for role in required_roles):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Required role missing.")

    is_global_admin = any(
        assignment.role.role_code == RoleCode.ADMIN and assignment.scope_type == ScopeType.GLOBAL
        for assignment in assignments
    )
    if is_global_admin and (access_group_id or workspace_id):
        log_audit_event(
            session,
            event_type="admin_bypass_applied",
            entity_type="authorization",
            entity_id=workspace_id or access_group_id,
            actor_user=user,
            payload={"workspace_id": str(workspace_id) if workspace_id else None},
        )

    if access_group_id and not is_global_admin:
        membership = session.scalar(
            select(GroupMembership).where(
                GroupMembership.access_group_id == access_group_id,
                GroupMembership.app_user_id == user.app_user_id,
                GroupMembership.membership_status == MembershipStatus.ACTIVE,
            )
        )
        if membership is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Active group membership required.")

    if workspace_id and participant_roles and not is_global_admin:
        participant = session.scalar(
            select(WorkspaceParticipant).where(
                WorkspaceParticipant.workspace_id == workspace_id,
                WorkspaceParticipant.app_user_id == user.app_user_id,
                WorkspaceParticipant.removed_at.is_(None),
                WorkspaceParticipant.participant_role.in_(participant_roles),
            )
        )
        if participant is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workspace participation required.")

    if settings.access_policy_enabled:
        now = datetime.now(UTC)
        decision = session.scalar(
            select(AccessPolicyDecision)
            .where(
                or_(
                    AccessPolicyDecision.app_user_id == user.app_user_id,
                    AccessPolicyDecision.company_person_id == user.company_person_id,
                ),
                or_(AccessPolicyDecision.expires_at.is_(None), AccessPolicyDecision.expires_at > now),
            )
            .order_by(AccessPolicyDecision.evaluated_at.desc())
        )
        if decision is None or decision.decision_type != AccessDecisionType.ALLOW:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access policy denied.")

    return [role.value for role in role_codes]
