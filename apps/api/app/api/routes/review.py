from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.enums import CommentVisibilityType, ParticipantRole, RoleCode
from app.db.models import AppUser, ClarificationRequest, Comment, FinalValue, LineItem, Recommendation, ValidationIssue, Workspace
from app.db.session import get_db
from app.schemas.api import (
    ClarificationAnswerRequest,
    ClarificationCreateRequest,
    CommentCreateRequest,
    LineItemFinalizeRequest,
    RecommendationCreateRequest,
    ValidationResolveRequest,
)
from app.services.authorization import authorize
from app.services.workflow import (
    answer_clarification,
    close_clarification,
    create_clarification,
    create_comment,
    create_recommendation,
    finalize_line_item,
    resolve_validation_issue,
)

router = APIRouter(tags=["review"])


@router.get("/workspaces/{workspace_id}/comments")
def list_workspace_comments(
    workspace_id: UUID,
    line_item_id: UUID | None = None,
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    workspace = db.get(Workspace, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found.")
    roles = authorize(
        session=db,
        user=current_user,
        required_roles=[],
        access_group_id=workspace.access_group_id,
        workspace_id=workspace.workspace_id,
        participant_roles=[ParticipantRole.SUBMITTER, ParticipantRole.REVIEWER, ParticipantRole.ADMIN, ParticipantRole.VIEWER],
    )
    query = select(Comment).where(Comment.workspace_id == workspace_id)
    if line_item_id:
        query = query.where(Comment.line_item_id == line_item_id)
    if "submitter" in roles and "reviewer" not in roles and "admin" not in roles:
        query = query.where(Comment.visibility_type == CommentVisibilityType.SUBMITTER_VISIBLE)
    comments = db.scalars(query.order_by(Comment.created_at)).all()
    return [
        {
            "comment_id": str(comment.comment_id),
            "line_item_id": str(comment.line_item_id) if comment.line_item_id else None,
            "clarification_request_id": str(comment.clarification_request_id) if comment.clarification_request_id else None,
            "visibility_type": comment.visibility_type.value,
            "comment_text": comment.comment_text,
            "created_at": comment.created_at.isoformat(),
        }
        for comment in comments
    ]


@router.get("/workspaces/{workspace_id}/clarifications")
def list_workspace_clarifications(
    workspace_id: UUID,
    line_item_id: UUID | None = None,
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    workspace = db.get(Workspace, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found.")
    authorize(
        session=db,
        user=current_user,
        required_roles=[],
        access_group_id=workspace.access_group_id,
        workspace_id=workspace.workspace_id,
        participant_roles=[ParticipantRole.SUBMITTER, ParticipantRole.REVIEWER, ParticipantRole.ADMIN, ParticipantRole.VIEWER],
    )
    query = select(ClarificationRequest).where(ClarificationRequest.workspace_id == workspace_id)
    if line_item_id:
        query = query.where(ClarificationRequest.line_item_id == line_item_id)
    clarifications = db.scalars(query.order_by(ClarificationRequest.created_at.desc())).all()
    return [
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
    ]


@router.post("/workspaces/{workspace_id}/line-items/{line_item_id}/comments", status_code=status.HTTP_201_CREATED)
def create_comment_route(
    workspace_id: UUID,
    line_item_id: UUID,
    payload: CommentCreateRequest,
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    workspace = db.get(Workspace, workspace_id)
    if workspace is None or db.get(LineItem, line_item_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace or line item not found.")
    roles = authorize(
        session=db,
        user=current_user,
        required_roles=[RoleCode.SUBMITTER, RoleCode.REVIEWER, RoleCode.ADMIN],
        access_group_id=workspace.access_group_id,
        workspace_id=workspace.workspace_id,
        participant_roles=[ParticipantRole.SUBMITTER, ParticipantRole.REVIEWER, ParticipantRole.ADMIN],
    )
    if "submitter" in roles and payload.visibility_type == CommentVisibilityType.INTERNAL_ONLY:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Submitter cannot post internal comments.")
    comment = create_comment(db, actor=current_user, workspace_id=workspace.workspace_id, line_item_id=line_item_id, payload=payload)
    db.commit()
    return {
        "comment_id": str(comment.comment_id),
        "visibility_type": comment.visibility_type.value,
        "comment_text": comment.comment_text,
    }


@router.post("/workspaces/{workspace_id}/line-items/{line_item_id}/clarifications", status_code=status.HTTP_201_CREATED)
def create_clarification_route(
    workspace_id: UUID,
    line_item_id: UUID,
    payload: ClarificationCreateRequest,
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    workspace = db.get(Workspace, workspace_id)
    if workspace is None or db.get(LineItem, line_item_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace or line item not found.")
    authorize(
        session=db,
        user=current_user,
        required_roles=[RoleCode.REVIEWER, RoleCode.ADMIN],
        access_group_id=workspace.access_group_id,
        workspace_id=workspace.workspace_id,
        participant_roles=[ParticipantRole.REVIEWER, ParticipantRole.ADMIN],
    )
    clarification = create_clarification(
        db, actor=current_user, workspace_id=workspace.workspace_id, line_item_id=line_item_id, payload=payload
    )
    db.commit()
    return {
        "clarification_request_id": str(clarification.clarification_request_id),
        "status": clarification.status.value,
        "message": clarification.message,
    }


@router.post("/clarifications/{clarification_id}/answer")
def answer_clarification_route(
    clarification_id: UUID,
    payload: ClarificationAnswerRequest,
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    clarification = db.get(ClarificationRequest, clarification_id)
    if clarification is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clarification not found.")
    workspace = db.get(Workspace, clarification.workspace_id)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found.")
    roles = authorize(
        session=db,
        user=current_user,
        required_roles=[RoleCode.SUBMITTER, RoleCode.ADMIN],
        access_group_id=workspace.access_group_id,
        workspace_id=workspace.workspace_id,
        participant_roles=[ParticipantRole.SUBMITTER, ParticipantRole.ADMIN],
    )
    if "submitter" in roles and payload.visibility_type == CommentVisibilityType.INTERNAL_ONLY:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Submitter cannot post internal comments.")
    answer_clarification(db, actor=current_user, clarification=clarification, payload=payload)
    db.commit()
    return {"clarification_request_id": str(clarification.clarification_request_id), "status": clarification.status.value}


@router.post("/clarifications/{clarification_id}/close")
def close_clarification_route(
    clarification_id: UUID,
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    clarification = db.get(ClarificationRequest, clarification_id)
    if clarification is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clarification not found.")
    workspace = db.get(Workspace, clarification.workspace_id)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found.")
    authorize(
        session=db,
        user=current_user,
        required_roles=[RoleCode.REVIEWER, RoleCode.ADMIN],
        access_group_id=workspace.access_group_id,
        workspace_id=workspace.workspace_id,
        participant_roles=[ParticipantRole.REVIEWER, ParticipantRole.ADMIN],
    )
    close_clarification(db, actor=current_user, clarification=clarification)
    db.commit()
    return {"clarification_request_id": str(clarification.clarification_request_id), "status": clarification.status.value}


@router.post("/line-items/{line_item_id}/recommendations", status_code=status.HTTP_201_CREATED)
def create_recommendation_route(
    line_item_id: UUID,
    payload: RecommendationCreateRequest,
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    line_item = db.get(LineItem, line_item_id)
    if line_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Line item not found.")
    workspace = db.get(Workspace, line_item.workspace_id)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found.")
    authorize(
        session=db,
        user=current_user,
        required_roles=[RoleCode.REVIEWER, RoleCode.ADMIN],
        access_group_id=workspace.access_group_id,
        workspace_id=workspace.workspace_id,
        participant_roles=[ParticipantRole.REVIEWER, ParticipantRole.ADMIN],
    )
    recommendation = create_recommendation(db, actor=current_user, line_item=line_item, payload=payload)
    db.commit()
    return {
        "recommendation_id": str(recommendation.recommendation_id),
        "recommended_action": recommendation.recommended_action.value,
    }


@router.get("/line-items/{line_item_id}/recommendations")
def list_recommendations(
    line_item_id: UUID,
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    line_item = db.get(LineItem, line_item_id)
    if line_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Line item not found.")
    workspace = db.get(Workspace, line_item.workspace_id)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found.")
    authorize(
        session=db,
        user=current_user,
        required_roles=[],
        access_group_id=workspace.access_group_id,
        workspace_id=workspace.workspace_id,
        participant_roles=[ParticipantRole.SUBMITTER, ParticipantRole.REVIEWER, ParticipantRole.ADMIN, ParticipantRole.VIEWER],
    )
    rows = db.scalars(
        select(Recommendation).where(Recommendation.line_item_id == line_item_id).order_by(Recommendation.created_at.desc())
    ).all()
    return [
        {
            "recommendation_id": str(recommendation.recommendation_id),
            "recommended_action": recommendation.recommended_action.value,
            "recommended_final_value_json": recommendation.recommended_final_value_json,
            "reason_text": recommendation.reason_text,
            "created_at": recommendation.created_at.isoformat(),
            "superseded_at": recommendation.superseded_at.isoformat() if recommendation.superseded_at else None,
        }
        for recommendation in rows
    ]


@router.get("/line-items/{line_item_id}/final-values")
def list_final_values(
    line_item_id: UUID,
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    line_item = db.get(LineItem, line_item_id)
    if line_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Line item not found.")
    workspace = db.get(Workspace, line_item.workspace_id)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found.")
    authorize(
        session=db,
        user=current_user,
        required_roles=[],
        access_group_id=workspace.access_group_id,
        workspace_id=workspace.workspace_id,
        participant_roles=[ParticipantRole.SUBMITTER, ParticipantRole.REVIEWER, ParticipantRole.ADMIN, ParticipantRole.VIEWER],
    )
    rows = db.scalars(select(FinalValue).where(FinalValue.line_item_id == line_item_id).order_by(FinalValue.approved_at.desc())).all()
    return [
        {
            "final_value_id": str(value.final_value_id),
            "source_workspace_revision_id": str(value.source_workspace_revision_id) if value.source_workspace_revision_id else None,
            "original_submitted_current_payload_id": str(value.original_submitted_current_payload_id) if value.original_submitted_current_payload_id else None,
            "final_value_json": value.final_value_json,
            "override_reason": value.override_reason,
            "approved_at": value.approved_at.isoformat(),
            "is_current": value.is_current,
            "superseded_at": value.superseded_at.isoformat() if value.superseded_at else None,
        }
        for value in rows
    ]


@router.post("/line-items/{line_item_id}/finalize")
def finalize_line_item_route(
    line_item_id: UUID,
    payload: LineItemFinalizeRequest,
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    line_item = db.get(LineItem, line_item_id)
    if line_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Line item not found.")
    workspace = db.get(Workspace, line_item.workspace_id)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found.")
    authorize(
        session=db,
        user=current_user,
        required_roles=[RoleCode.ADMIN],
        access_group_id=workspace.access_group_id,
        workspace_id=workspace.workspace_id,
        participant_roles=[ParticipantRole.ADMIN],
    )
    finalize_line_item(db, actor=current_user, line_item=line_item, payload=payload)
    db.commit()
    return {"line_item_id": str(line_item.line_item_id), "line_item_status": line_item.line_item_status.value}


@router.post("/line-items/{line_item_id}/status")
def change_line_item_status_route(
    line_item_id: UUID,
    payload: LineItemFinalizeRequest,
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return finalize_line_item_route(
        line_item_id=line_item_id,
        payload=payload,
        current_user=current_user,
        db=db,
    )


@router.get("/workspaces/{workspace_id}/validation-issues")
def list_validation_issues(
    workspace_id: UUID,
    line_item_id: UUID | None = None,
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    workspace = db.get(Workspace, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found.")
    authorize(
        session=db,
        user=current_user,
        required_roles=[],
        access_group_id=workspace.access_group_id,
        workspace_id=workspace.workspace_id,
        participant_roles=[ParticipantRole.SUBMITTER, ParticipantRole.REVIEWER, ParticipantRole.ADMIN, ParticipantRole.VIEWER],
    )
    query = select(ValidationIssue).where(ValidationIssue.workspace_id == workspace_id)
    if line_item_id:
        query = query.where(ValidationIssue.line_item_id == line_item_id)
    issues = db.scalars(query.order_by(ValidationIssue.created_at.desc())).all()
    return [
        {
            "validation_issue_id": str(issue.validation_issue_id),
            "line_item_id": str(issue.line_item_id) if issue.line_item_id else None,
            "severity": issue.severity.value,
            "rule_code": issue.rule_code,
            "message_he": issue.message_he,
            "message_en": issue.message_en,
            "status": issue.status.value,
            "created_at": issue.created_at.isoformat(),
            "resolved_at": issue.resolved_at.isoformat() if issue.resolved_at else None,
        }
        for issue in issues
    ]


@router.post("/validation/{validation_issue_id}/resolve")
def resolve_validation_issue_route(
    validation_issue_id: UUID,
    payload: ValidationResolveRequest | None = None,
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    issue = db.get(ValidationIssue, validation_issue_id)
    if issue is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Validation issue not found.")
    workspace = db.get(Workspace, issue.workspace_id)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found.")
    authorize(
        session=db,
        user=current_user,
        required_roles=[RoleCode.REVIEWER, RoleCode.ADMIN],
        access_group_id=workspace.access_group_id,
        workspace_id=workspace.workspace_id,
        participant_roles=[ParticipantRole.REVIEWER, ParticipantRole.ADMIN],
    )
    resolve_validation_issue(db, actor=current_user, issue=issue)
    db.commit()
    return {
        "validation_issue_id": str(issue.validation_issue_id),
        "status": issue.status.value,
        "resolution_note": payload.resolution_note if payload else None,
    }
