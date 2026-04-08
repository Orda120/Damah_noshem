from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.db.enums import (
    AttemptStatus,
    CommentVisibilityType,
    LineItemStatus,
    MembershipRole,
    MembershipStatus,
    ParticipantRole,
    RevisionReason,
    WorkspaceStatus,
)
from app.db.models import (
    AccessCode,
    AccessGroup,
    AppUser,
    Artifact,
    ArtifactLink,
    ClarificationRequest,
    Comment,
    CurrentPayload,
    FinalValue,
    GroupCreationEvent,
    GroupMembership,
    LineItem,
    LineItemStatusHistory,
    OutputBatch,
    Recommendation,
    Template,
    TemplateFieldDefinition,
    TemplateSchemaSnapshot,
    ValidationIssue,
    Workspace,
    WorkspaceParticipant,
    WorkspaceRevision,
    WorkspaceStatusHistory,
)
from app.schemas.api import (
    ClarificationAnswerRequest,
    ClarificationCreateRequest,
    CommentCreateRequest,
    GroupCreateRequest,
    LineItemCreateInput,
    LineItemFinalizeRequest,
    MembershipGrantRequest,
    ParticipantInput,
    PayloadSaveRequest,
    RecommendationCreateRequest,
    TemplateCreateRequest,
    TemplateUpdateRequest,
    WorkspaceCreateRequest,
    WorkspaceStatusChangeRequest,
)
from app.services.audit import log_audit_event
from app.services.validation import get_open_blocking_issues, replace_validation_issues


def hash_access_code(raw_code: str) -> str:
    return hashlib.sha256(raw_code.encode("utf-8")).hexdigest()


def create_group(session: Session, *, actor: AppUser, payload: GroupCreateRequest) -> AccessGroup:
    access_code = session.scalar(
        select(AccessCode).where(AccessCode.code_value_hash == hash_access_code(payload.access_code))
    )
    now = datetime.now(UTC)
    if (
        access_code is None
        or access_code.is_revoked
        or (access_code.expires_at is not None and access_code.expires_at <= now)
        or access_code.use_count >= access_code.max_uses
    ):
        event = GroupCreationEvent(
            access_code_id=access_code.access_code_id if access_code else None,
            created_by_user_id=actor.app_user_id,
            attempt_status=AttemptStatus.FAILED,
            failure_reason="invalid_or_expired_access_code",
        )
        session.add(event)
        log_audit_event(
            session,
            event_type="group_creation_failed",
            entity_type="access_group",
            entity_id=None,
            actor_user=actor,
            payload={"group_name": payload.group_name},
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired access code.")

    group = AccessGroup(
        group_name=payload.group_name,
        group_description=payload.group_description,
        created_by_user_id=actor.app_user_id,
    )
    session.add(group)
    session.flush()

    membership = GroupMembership(
        access_group_id=group.access_group_id,
        app_user_id=actor.app_user_id,
        membership_role=MembershipRole.GROUP_ADMIN,
        membership_status=MembershipStatus.ACTIVE,
        granted_by_user_id=actor.app_user_id,
    )
    session.add(membership)
    access_code.use_count += 1
    session.add(
        GroupCreationEvent(
            access_code_id=access_code.access_code_id,
            created_group_id=group.access_group_id,
            created_by_user_id=actor.app_user_id,
            attempt_status=AttemptStatus.SUCCESS,
        )
    )
    log_audit_event(
        session,
        event_type="group_created",
        entity_type="access_group",
        entity_id=group.access_group_id,
        actor_user=actor,
        payload={"group_name": payload.group_name},
    )
    return group


def grant_group_membership(
    session: Session,
    *,
    actor: AppUser,
    group_id: UUID,
    payload: MembershipGrantRequest,
) -> GroupMembership:
    membership = GroupMembership(
        access_group_id=group_id,
        app_user_id=payload.app_user_id,
        membership_role=payload.membership_role,
        membership_status=MembershipStatus.ACTIVE,
        granted_by_user_id=actor.app_user_id,
    )
    session.add(membership)
    session.flush()
    log_audit_event(
        session,
        event_type="group_membership_granted",
        entity_type="group_membership",
        entity_id=membership.group_membership_id,
        actor_user=actor,
        payload={"group_id": str(group_id), "app_user_id": str(payload.app_user_id)},
    )
    return membership


def revoke_group_membership(session: Session, *, actor: AppUser, membership: GroupMembership) -> GroupMembership:
    membership.membership_status = MembershipStatus.REVOKED
    membership.revoked_at = datetime.now(UTC)
    membership.revoked_by_user_id = actor.app_user_id
    log_audit_event(
        session,
        event_type="group_membership_revoked",
        entity_type="group_membership",
        entity_id=membership.group_membership_id,
        actor_user=actor,
        payload={"group_id": str(membership.access_group_id)},
    )
    return membership


def create_template(session: Session, *, actor: AppUser, payload: TemplateCreateRequest) -> Template:
    template = Template(
        template_code=payload.template_code,
        template_name_he=payload.template_name_he,
        template_name_en=payload.template_name_en,
        template_status=payload.template_status,
        created_by_user_id=actor.app_user_id,
        field_definitions=[
            TemplateFieldDefinition(**field.model_dump()) for field in payload.field_definitions
        ],
    )
    session.add(template)
    session.flush()
    return template


def update_template(
    session: Session,
    *,
    actor: AppUser,
    template: Template,
    payload: TemplateUpdateRequest,
) -> Template:
    previous_schema = {
        "template_code": template.template_code,
        "version_number": template.version_number,
        "field_definitions": [
            {
                "field_key": field.field_key,
                "field_type": field.field_type.value,
                "validation_rule_ref": field.validation_rule_ref,
            }
            for field in template.field_definitions
        ],
    }
    if payload.template_name_he is not None:
        template.template_name_he = payload.template_name_he
    if payload.template_name_en is not None:
        template.template_name_en = payload.template_name_en
    if payload.template_status is not None:
        template.template_status = payload.template_status
    if payload.field_definitions is not None:
        template.version_number += 1
        session.add(
            TemplateSchemaSnapshot(
                template_id=template.template_id,
                template_version_number=template.version_number - 1,
                schema_json=previous_schema,
                created_by_user_id=actor.app_user_id,
            )
        )
        template.field_definitions.clear()
        template.field_definitions.extend(
            [TemplateFieldDefinition(**field.model_dump()) for field in payload.field_definitions]
        )
    return template


def create_workspace(session: Session, *, actor: AppUser, payload: WorkspaceCreateRequest) -> Workspace:
    group = session.get(AccessGroup, payload.access_group_id)
    template = session.get(Template, payload.template_id)
    if group is None or template is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid group or template.")

    participant_user_ids = {participant.app_user_id for participant in payload.participants}
    if participant_user_ids:
        users_count = session.scalar(
            select(func.count(AppUser.app_user_id)).where(AppUser.app_user_id.in_(participant_user_ids))
        )
        if users_count != len(participant_user_ids):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="One or more participants are invalid.")

    workspace = Workspace(
        access_group_id=payload.access_group_id,
        template_id=payload.template_id,
        workspace_title=payload.workspace_title,
        business_date=payload.business_date,
        workspace_status=WorkspaceStatus.ACTIVE,
        created_by_user_id=actor.app_user_id,
    )
    session.add(workspace)
    session.flush()
    session.add(
        WorkspaceStatusHistory(
            workspace_id=workspace.workspace_id,
            from_status=None,
            to_status=workspace.workspace_status.value,
            changed_by_user_id=actor.app_user_id,
        )
    )
    for participant in payload.participants:
        session.add(
            WorkspaceParticipant(
                workspace_id=workspace.workspace_id,
                app_user_id=participant.app_user_id,
                participant_role=participant.participant_role,
                assigned_by_user_id=actor.app_user_id,
            )
        )
    for line_item in payload.line_items:
        created = LineItem(
            workspace_id=workspace.workspace_id,
            line_item_key=line_item.line_item_key,
            line_item_title=line_item.line_item_title,
            line_item_status=LineItemStatus.OPEN,
            created_by_user_id=actor.app_user_id,
        )
        session.add(created)
        session.flush()
        session.add(
            LineItemStatusHistory(
                line_item_id=created.line_item_id,
                from_status=None,
                to_status=created.line_item_status.value,
                changed_by_user_id=actor.app_user_id,
            )
        )
    log_audit_event(
        session,
        event_type="workspace_created",
        entity_type="workspace",
        entity_id=workspace.workspace_id,
        actor_user=actor,
        payload={"line_item_count": len(payload.line_items)},
    )
    return workspace


def change_workspace_status(
    session: Session,
    *,
    actor: AppUser,
    workspace: Workspace,
    payload: WorkspaceStatusChangeRequest,
) -> Workspace:
    previous = workspace.workspace_status.value
    workspace.workspace_status = payload.workspace_status
    if payload.workspace_status == WorkspaceStatus.CLOSED:
        workspace.closed_at = datetime.now(UTC)
        workspace.closed_by_user_id = actor.app_user_id
    session.add(
        WorkspaceStatusHistory(
            workspace_id=workspace.workspace_id,
            from_status=previous,
            to_status=payload.workspace_status.value,
            changed_by_user_id=actor.app_user_id,
            change_reason=payload.change_reason,
        )
    )
    log_audit_event(
        session,
        event_type="workspace_status_changed",
        entity_type="workspace",
        entity_id=workspace.workspace_id,
        actor_user=actor,
        payload={"from_status": previous, "to_status": payload.workspace_status.value},
    )
    return workspace


def add_workspace_participant(
    session: Session,
    *,
    actor: AppUser,
    workspace_id: UUID,
    participant: ParticipantInput,
) -> WorkspaceParticipant:
    row = WorkspaceParticipant(
        workspace_id=workspace_id,
        app_user_id=participant.app_user_id,
        participant_role=participant.participant_role,
        assigned_by_user_id=actor.app_user_id,
    )
    session.add(row)
    session.flush()
    return row


def add_line_item(
    session: Session,
    *,
    actor: AppUser,
    workspace_id: UUID,
    payload: LineItemCreateInput,
) -> LineItem:
    row = LineItem(
        workspace_id=workspace_id,
        line_item_key=payload.line_item_key,
        line_item_title=payload.line_item_title,
        line_item_status=LineItemStatus.OPEN,
        created_by_user_id=actor.app_user_id,
    )
    session.add(row)
    session.flush()
    session.add(
        LineItemStatusHistory(
            line_item_id=row.line_item_id,
            from_status=None,
            to_status=row.line_item_status.value,
            changed_by_user_id=actor.app_user_id,
        )
    )
    return row


def _resolve_actor_editability(
    *,
    actor_roles: set[str],
    participant_role: ParticipantRole | None,
    line_item_status: LineItemStatus,
    field: TemplateFieldDefinition,
) -> bool:
    if line_item_status == LineItemStatus.DONE and field.lock_on_done:
        return False
    if line_item_status == LineItemStatus.CLOSED and field.lock_on_closed:
        return False
    if "admin" in actor_roles:
        return field.admin_editable
    if participant_role == ParticipantRole.REVIEWER:
        return field.reviewer_editable
    if participant_role == ParticipantRole.SUBMITTER:
        return field.submitter_editable
    return False


def save_payload_revision(
    session: Session,
    *,
    actor: AppUser,
    workspace: Workspace,
    line_item: LineItem,
    template: Template,
    payload: PayloadSaveRequest,
    actor_roles: set[str],
    participant_role: ParticipantRole | None,
) -> tuple[WorkspaceRevision, CurrentPayload, list[ValidationIssue]]:
    latest_revision_number = session.scalar(
        select(func.max(WorkspaceRevision.revision_number)).where(WorkspaceRevision.workspace_id == workspace.workspace_id)
    )
    current_revision_number = latest_revision_number or 0
    if payload.expected_revision_number != current_revision_number:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Revision number mismatch.")

    for field in template.field_definitions:
        if field.field_key in payload.payload_json and not _resolve_actor_editability(
            actor_roles=actor_roles,
            participant_role=participant_role,
            line_item_status=line_item.line_item_status,
            field=field,
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Field '{field.field_key}' cannot be edited in the current role/state.",
            )

    revision = WorkspaceRevision(
        workspace_id=workspace.workspace_id,
        revision_number=current_revision_number + 1,
        created_by_user_id=actor.app_user_id,
        revision_reason=payload.revision_reason,
    )
    session.add(revision)
    session.flush()
    session.execute(
        update(CurrentPayload)
        .where(
            CurrentPayload.workspace_id == workspace.workspace_id,
            CurrentPayload.line_item_id == line_item.line_item_id,
            CurrentPayload.is_current.is_(True),
        )
        .values(is_current=False)
    )
    current_payload = CurrentPayload(
        workspace_id=workspace.workspace_id,
        line_item_id=line_item.line_item_id,
        workspace_revision_id=revision.workspace_revision_id,
        template_id=template.template_id,
        payload_json=payload.payload_json,
        is_current=True,
    )
    session.add(current_payload)
    session.flush()
    issues = replace_validation_issues(
        session,
        template=template,
        workspace_id=workspace.workspace_id,
        line_item_id=line_item.line_item_id,
        workspace_revision=revision,
        payload_json=payload.payload_json,
    )
    log_audit_event(
        session,
        event_type="workspace_revision_created",
        entity_type="workspace_revision",
        entity_id=revision.workspace_revision_id,
        actor_user=actor,
        payload={"workspace_id": str(workspace.workspace_id), "line_item_id": str(line_item.line_item_id)},
    )
    return revision, current_payload, issues


def create_comment(
    session: Session,
    *,
    actor: AppUser,
    workspace_id: UUID,
    line_item_id: UUID | None,
    payload: CommentCreateRequest,
) -> Comment:
    comment = Comment(
        workspace_id=workspace_id,
        line_item_id=line_item_id,
        clarification_request_id=payload.clarification_request_id,
        author_user_id=actor.app_user_id,
        visibility_type=payload.visibility_type,
        comment_text=payload.comment_text,
    )
    session.add(comment)
    session.flush()
    log_audit_event(
        session,
        event_type="comment_created",
        entity_type="comment",
        entity_id=comment.comment_id,
        actor_user=actor,
        payload={"visibility_type": payload.visibility_type.value},
    )
    return comment


def create_clarification(
    session: Session,
    *,
    actor: AppUser,
    workspace_id: UUID,
    line_item_id: UUID,
    payload: ClarificationCreateRequest,
) -> ClarificationRequest:
    clarification = ClarificationRequest(
        workspace_id=workspace_id,
        line_item_id=line_item_id,
        requested_by_user_id=actor.app_user_id,
        message=payload.message,
    )
    session.add(clarification)
    session.flush()
    session.add(
        Comment(
            workspace_id=workspace_id,
            line_item_id=line_item_id,
            clarification_request_id=clarification.clarification_request_id,
            author_user_id=actor.app_user_id,
            visibility_type=CommentVisibilityType.SUBMITTER_VISIBLE,
            comment_text=payload.message,
        )
    )
    log_audit_event(
        session,
        event_type="clarification_requested",
        entity_type="clarification_request",
        entity_id=clarification.clarification_request_id,
        actor_user=actor,
        payload={"line_item_id": str(line_item_id)},
    )
    return clarification


def answer_clarification(
    session: Session,
    *,
    actor: AppUser,
    clarification: ClarificationRequest,
    payload: ClarificationAnswerRequest,
) -> ClarificationRequest:
    clarification.status = clarification.status.__class__.ANSWERED
    clarification.answered_at = datetime.now(UTC)
    session.add(
        Comment(
            workspace_id=clarification.workspace_id,
            line_item_id=clarification.line_item_id,
            clarification_request_id=clarification.clarification_request_id,
            author_user_id=actor.app_user_id,
            visibility_type=payload.visibility_type,
            comment_text=payload.answer_text,
        )
    )
    log_audit_event(
        session,
        event_type="clarification_answered",
        entity_type="clarification_request",
        entity_id=clarification.clarification_request_id,
        actor_user=actor,
    )
    return clarification


def close_clarification(session: Session, *, actor: AppUser, clarification: ClarificationRequest) -> ClarificationRequest:
    clarification.status = clarification.status.__class__.CLOSED
    clarification.closed_at = datetime.now(UTC)
    log_audit_event(
        session,
        event_type="clarification_closed",
        entity_type="clarification_request",
        entity_id=clarification.clarification_request_id,
        actor_user=actor,
    )
    return clarification


def create_recommendation(
    session: Session,
    *,
    actor: AppUser,
    line_item: LineItem,
    payload: RecommendationCreateRequest,
) -> Recommendation:
    current = session.scalar(
        select(Recommendation).where(
            Recommendation.line_item_id == line_item.line_item_id,
            Recommendation.superseded_at.is_(None),
        )
    )
    if current is not None:
        current.superseded_at = datetime.now(UTC)
    recommendation = Recommendation(
        line_item_id=line_item.line_item_id,
        recommended_by_user_id=actor.app_user_id,
        recommended_action=payload.recommended_action,
        recommended_final_value_json=payload.recommended_final_value_json,
        reason_text=payload.reason_text,
    )
    session.add(recommendation)
    session.flush()
    log_audit_event(
        session,
        event_type="recommendation_created",
        entity_type="recommendation",
        entity_id=recommendation.recommendation_id,
        actor_user=actor,
        payload={"line_item_id": str(line_item.line_item_id)},
    )
    return recommendation


def finalize_line_item(
    session: Session,
    *,
    actor: AppUser,
    line_item: LineItem,
    payload: LineItemFinalizeRequest,
) -> LineItem:
    previous_status = line_item.line_item_status
    current_payload = session.scalar(
        select(CurrentPayload).where(
            CurrentPayload.line_item_id == line_item.line_item_id,
            CurrentPayload.is_current.is_(True),
        )
    )
    if payload.action == LineItemStatus.DONE:
        blocking_issues = get_open_blocking_issues(session, line_item=line_item)
        if blocking_issues:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Blocking validation issues remain open.",
            )
        if current_payload is None and payload.final_value_json is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Final value is required.")
        current_final_value = session.scalar(
            select(FinalValue).where(
                FinalValue.line_item_id == line_item.line_item_id,
                FinalValue.is_current.is_(True),
            )
        )
        if current_final_value is not None:
            current_final_value.is_current = False
            current_final_value.superseded_at = datetime.now(UTC)
        new_final_value = FinalValue(
            line_item_id=line_item.line_item_id,
            source_workspace_revision_id=current_payload.workspace_revision_id if current_payload else None,
            original_submitted_current_payload_id=current_payload.current_payload_id if current_payload else None,
            final_value_json=payload.final_value_json or current_payload.payload_json or {},
            override_reason=payload.override_reason,
            approved_by_user_id=actor.app_user_id,
            is_current=True,
        )
        session.add(new_final_value)
        session.flush()
        if current_final_value is not None:
            current_final_value.superseded_by_final_value_id = new_final_value.final_value_id
        log_audit_event(
            session,
            event_type="final_value_created",
            entity_type="final_value",
            entity_id=new_final_value.final_value_id,
            actor_user=actor,
            payload={"line_item_id": str(line_item.line_item_id)},
        )
    elif payload.action not in {LineItemStatus.CLOSED, LineItemStatus.OPEN, LineItemStatus.ARCHIVED}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported line item action.")

    line_item.line_item_status = payload.action
    if payload.action == LineItemStatus.CLOSED:
        line_item.closed_reason = payload.change_reason
    session.add(
        LineItemStatusHistory(
            line_item_id=line_item.line_item_id,
            from_status=previous_status.value,
            to_status=payload.action.value,
            changed_by_user_id=actor.app_user_id,
            change_reason=payload.change_reason,
        )
    )
    log_audit_event(
        session,
        event_type="line_item_status_changed",
        entity_type="line_item",
        entity_id=line_item.line_item_id,
        actor_user=actor,
        payload={"from_status": previous_status.value, "to_status": payload.action.value},
    )
    return line_item


def resolve_validation_issue(session: Session, *, actor: AppUser, issue: ValidationIssue) -> ValidationIssue:
    issue.status = issue.status.__class__.RESOLVED
    issue.resolved_at = datetime.now(UTC)
    issue.resolved_by_user_id = actor.app_user_id
    log_audit_event(
        session,
        event_type="validation_issue_resolved",
        entity_type="validation_issue",
        entity_id=issue.validation_issue_id,
        actor_user=actor,
    )
    return issue
