from __future__ import annotations

from collections import defaultdict

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.db.enums import CommentVisibilityType
from app.db.models import (
    AppUser,
    AuditEvent,
    ClarificationRequest,
    Comment,
    CurrentPayload,
    FinalValue,
    GroupMembership,
    LineItem,
    Recommendation,
    Template,
    TemplateFieldDefinition,
    ValidationIssue,
    Workspace,
    WorkspaceParticipant,
    WorkspaceRevision,
)


def serialize_user(user: AppUser, roles: list[str], session_token: str | None = None) -> dict:
    return {
        "app_user_id": str(user.app_user_id),
        "employee_number": user.company_person.employee_number,
        "full_name_he": user.company_person.full_name_he,
        "full_name_en": user.company_person.full_name_en,
        "email": user.company_person.email,
        "default_language": user.default_language.value,
        "roles": roles,
        "session_token": session_token,
    }


def serialize_template(template: Template) -> dict:
    return {
        "template_id": str(template.template_id),
        "template_code": template.template_code,
        "template_name_he": template.template_name_he,
        "template_name_en": template.template_name_en,
        "template_status": template.template_status.value,
        "version_number": template.version_number,
        "field_definitions": [
            {
                "template_field_definition_id": str(field.template_field_definition_id),
                "field_key": field.field_key,
                "field_label_he": field.field_label_he,
                "field_label_en": field.field_label_en,
                "field_type": field.field_type.value,
                "is_required": field.is_required,
                "is_conditionally_required": field.is_conditionally_required,
                "submitter_editable": field.submitter_editable,
                "reviewer_editable": field.reviewer_editable,
                "admin_editable": field.admin_editable,
                "lock_on_done": field.lock_on_done,
                "lock_on_closed": field.lock_on_closed,
                "display_order": field.display_order,
                "validation_rule_ref": field.validation_rule_ref,
            }
            for field in template.field_definitions
        ],
    }


def serialize_group_membership(membership: GroupMembership) -> dict:
    return {
        "group_membership_id": str(membership.group_membership_id),
        "access_group_id": str(membership.access_group_id),
        "app_user_id": str(membership.app_user_id),
        "membership_role": membership.membership_role.value,
        "membership_status": membership.membership_status.value,
        "granted_at": membership.granted_at.isoformat(),
        "revoked_at": membership.revoked_at.isoformat() if membership.revoked_at else None,
    }


def serialize_workspace_detail(
    *,
    session: Session,
    workspace: Workspace,
    template: Template,
    submitter_view: bool,
) -> dict:
    line_items = session.scalars(
        select(LineItem).where(LineItem.workspace_id == workspace.workspace_id).order_by(LineItem.created_at)
    ).all()
    participants = session.scalars(
        select(WorkspaceParticipant).where(WorkspaceParticipant.workspace_id == workspace.workspace_id)
    ).all()
    revisions = session.scalars(
        select(WorkspaceRevision)
        .where(WorkspaceRevision.workspace_id == workspace.workspace_id)
        .order_by(WorkspaceRevision.revision_number.desc())
    ).all()
    payloads = session.scalars(
        select(CurrentPayload)
        .where(CurrentPayload.workspace_id == workspace.workspace_id)
        .order_by(CurrentPayload.created_at.desc())
    ).all()
    comments_query: Select[tuple[Comment]] = select(Comment).where(Comment.workspace_id == workspace.workspace_id)
    if submitter_view:
        comments_query = comments_query.where(
            Comment.visibility_type == CommentVisibilityType.SUBMITTER_VISIBLE
        )
    comments = session.scalars(comments_query.order_by(Comment.created_at)).all()
    clarifications = session.scalars(
        select(ClarificationRequest)
        .where(ClarificationRequest.workspace_id == workspace.workspace_id)
        .order_by(ClarificationRequest.created_at.desc())
    ).all()
    recommendations = session.scalars(
        select(Recommendation).join(LineItem, Recommendation.line_item_id == LineItem.line_item_id).where(
            LineItem.workspace_id == workspace.workspace_id
        )
    ).all()
    final_values = session.scalars(
        select(FinalValue).join(LineItem, FinalValue.line_item_id == LineItem.line_item_id).where(
            LineItem.workspace_id == workspace.workspace_id
        )
    ).all()
    issues = session.scalars(
        select(ValidationIssue)
        .where(ValidationIssue.workspace_id == workspace.workspace_id)
        .order_by(ValidationIssue.created_at.desc())
    ).all()

    payload_by_line_item: dict[str, list[dict]] = defaultdict(list)
    for payload in payloads:
        key = str(payload.line_item_id) if payload.line_item_id else "workspace"
        payload_by_line_item[key].append(
            {
                "current_payload_id": str(payload.current_payload_id),
                "workspace_revision_id": str(payload.workspace_revision_id),
                "line_item_id": str(payload.line_item_id) if payload.line_item_id else None,
                "payload_json": payload.payload_json,
                "payload_archived": payload.payload_archived,
                "payload_artifact_id": str(payload.payload_artifact_id) if payload.payload_artifact_id else None,
                "is_current": payload.is_current,
                "created_at": payload.created_at.isoformat(),
                "archived_at": payload.archived_at.isoformat() if payload.archived_at else None,
            }
        )

    return {
        "workspace_id": str(workspace.workspace_id),
        "workspace_title": workspace.workspace_title,
        "business_date": workspace.business_date.isoformat() if workspace.business_date else None,
        "workspace_status": workspace.workspace_status.value,
        "access_group_id": str(workspace.access_group_id),
        "template": serialize_template(template),
        "participants": [
            {
                "workspace_participant_id": str(participant.workspace_participant_id),
                "app_user_id": str(participant.app_user_id),
                "participant_role": participant.participant_role.value,
                "assigned_at": participant.assigned_at.isoformat(),
                "removed_at": participant.removed_at.isoformat() if participant.removed_at else None,
            }
            for participant in participants
        ],
        "line_items": [
            {
                "line_item_id": str(item.line_item_id),
                "line_item_key": item.line_item_key,
                "line_item_title": item.line_item_title,
                "line_item_status": item.line_item_status.value,
                "closed_reason": item.closed_reason,
                "payloads": payload_by_line_item.get(str(item.line_item_id), []),
                "recommendations": [
                    {
                        "recommendation_id": str(rec.recommendation_id),
                        "recommended_action": rec.recommended_action.value,
                        "recommended_final_value_json": rec.recommended_final_value_json,
                        "reason_text": rec.reason_text,
                        "created_at": rec.created_at.isoformat(),
                        "superseded_at": rec.superseded_at.isoformat() if rec.superseded_at else None,
                    }
                    for rec in recommendations
                    if rec.line_item_id == item.line_item_id
                ],
                "final_values": [
                    {
                        "final_value_id": str(final_value.final_value_id),
                        "final_value_json": final_value.final_value_json,
                        "override_reason": final_value.override_reason,
                        "approved_at": final_value.approved_at.isoformat(),
                        "is_current": final_value.is_current,
                    }
                    for final_value in final_values
                    if final_value.line_item_id == item.line_item_id
                ],
                "validation_issues": [
                    {
                        "validation_issue_id": str(issue.validation_issue_id),
                        "severity": issue.severity.value,
                        "rule_code": issue.rule_code,
                        "message_he": issue.message_he,
                        "message_en": issue.message_en,
                        "status": issue.status.value,
                    }
                    for issue in issues
                    if issue.line_item_id == item.line_item_id
                ],
            }
            for item in line_items
        ],
        "workspace_payloads": payload_by_line_item.get("workspace", []),
        "clarifications": [
            {
                "clarification_request_id": str(clarification.clarification_request_id),
                "line_item_id": str(clarification.line_item_id) if clarification.line_item_id else None,
                "status": clarification.status.value,
                "message": clarification.message,
                "created_at": clarification.created_at.isoformat(),
                "answered_at": clarification.answered_at.isoformat() if clarification.answered_at else None,
                "closed_at": clarification.closed_at.isoformat() if clarification.closed_at else None,
            }
            for clarification in clarifications
        ],
        "comments": [
            {
                "comment_id": str(comment.comment_id),
                "line_item_id": str(comment.line_item_id) if comment.line_item_id else None,
                "clarification_request_id": (
                    str(comment.clarification_request_id) if comment.clarification_request_id else None
                ),
                "visibility_type": comment.visibility_type.value,
                "comment_text": comment.comment_text,
                "created_at": comment.created_at.isoformat(),
            }
            for comment in comments
        ],
        "revisions": [
            {
                "workspace_revision_id": str(revision.workspace_revision_id),
                "revision_number": revision.revision_number,
                "revision_reason": revision.revision_reason.value,
                "created_at": revision.created_at.isoformat(),
            }
            for revision in revisions
        ],
    }


def serialize_audit_event(event: AuditEvent) -> dict:
    return {
        "audit_event_id": str(event.audit_event_id),
        "event_type": event.event_type,
        "entity_type": event.entity_type,
        "entity_id": str(event.entity_id) if event.entity_id else None,
        "actor_user_id": str(event.actor_user_id) if event.actor_user_id else None,
        "company_person_id": str(event.company_person_id) if event.company_person_id else None,
        "event_payload_json": event.event_payload_json,
        "created_at": event.created_at.isoformat(),
    }
