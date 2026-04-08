from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.enums import CommentVisibilityType, ParticipantRole, RoleCode
from app.db.models import AppUser, ClarificationRequest, LineItem, ValidationIssue, Workspace
from app.db.session import get_db
from app.schemas.api import (
    ClarificationAnswerRequest,
    ClarificationCreateRequest,
    CommentCreateRequest,
    LineItemFinalizeRequest,
    RecommendationCreateRequest,
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


@router.post("/validation/{validation_issue_id}/resolve")
def resolve_validation_issue_route(
    validation_issue_id: UUID,
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    issue = db.get(ValidationIssue, validation_issue_id)
    if issue is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Validation issue not found.")
    workspace = db.get(Workspace, issue.workspace_id)
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
    return {"validation_issue_id": str(issue.validation_issue_id), "status": issue.status.value}
