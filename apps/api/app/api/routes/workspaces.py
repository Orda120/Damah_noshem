from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.db.enums import ParticipantRole, RoleCode
from app.db.models import AppUser, CurrentPayload, LineItem, Template, Workspace, WorkspaceParticipant, WorkspaceRevision
from app.db.session import get_db
from app.schemas.api import (
    LineItemCreateInput,
    LineItemUpdateRequest,
    ParticipantInput,
    PayloadSaveRequest,
    WorkspaceCreateRequest,
    WorkspaceStatusChangeRequest,
    WorkspaceUpdateRequest,
)
from app.schemas.serializers import serialize_workspace_detail
from app.services.authorization import authorize
from app.services.workflow import (
    add_line_item,
    add_workspace_participant,
    change_workspace_status,
    create_workspace,
    save_payload_revision,
    update_line_item,
    update_workspace,
)

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.get("")
def list_workspaces(current_user: AppUser = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict]:
    roles = authorize(session=db, user=current_user, required_roles=[])
    query = select(Workspace).order_by(Workspace.created_at.desc())
    if "admin" not in roles:
        query = (
            select(Workspace)
            .join(WorkspaceParticipant, WorkspaceParticipant.workspace_id == Workspace.workspace_id)
            .where(
                WorkspaceParticipant.app_user_id == current_user.app_user_id,
                WorkspaceParticipant.removed_at.is_(None),
            )
            .order_by(Workspace.created_at.desc())
        )
    workspaces = db.scalars(query).all()
    return [
        {
            "workspace_id": str(workspace.workspace_id),
            "workspace_title": workspace.workspace_title,
            "business_date": workspace.business_date.isoformat() if workspace.business_date else None,
            "workspace_status": workspace.workspace_status.value,
            "access_group_id": str(workspace.access_group_id),
            "template_id": str(workspace.template_id),
        }
        for workspace in workspaces
    ]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_workspace_route(
    payload: WorkspaceCreateRequest,
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    authorize(session=db, user=current_user, required_roles=[RoleCode.ADMIN], access_group_id=payload.access_group_id)
    workspace = create_workspace(db, actor=current_user, payload=payload)
    db.commit()
    template = db.get(Template, workspace.template_id)
    return serialize_workspace_detail(session=db, workspace=workspace, template=template, submitter_view=False)


@router.get("/{workspace_id}")
def get_workspace(
    workspace_id: UUID,
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
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
    template = db.scalar(
        select(Template).options(selectinload(Template.field_definitions)).where(Template.template_id == workspace.template_id)
    )
    submitter_view = "submitter" in roles and "reviewer" not in roles and "admin" not in roles
    return serialize_workspace_detail(session=db, workspace=workspace, template=template, submitter_view=submitter_view)


@router.patch("/{workspace_id}")
def update_workspace_route(
    workspace_id: UUID,
    payload: WorkspaceUpdateRequest,
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    workspace = db.get(Workspace, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found.")
    authorize(session=db, user=current_user, required_roles=[RoleCode.ADMIN], access_group_id=workspace.access_group_id)
    update_workspace(db, workspace=workspace, payload=payload)
    db.commit()
    template = db.scalar(
        select(Template).options(selectinload(Template.field_definitions)).where(Template.template_id == workspace.template_id)
    )
    return serialize_workspace_detail(session=db, workspace=workspace, template=template, submitter_view=False)


@router.post("/{workspace_id}/participants", status_code=status.HTTP_201_CREATED)
def add_participant_route(
    workspace_id: UUID,
    payload: ParticipantInput,
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    workspace = db.get(Workspace, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found.")
    authorize(session=db, user=current_user, required_roles=[RoleCode.ADMIN], access_group_id=workspace.access_group_id)
    participant = add_workspace_participant(db, actor=current_user, workspace_id=workspace.workspace_id, participant=payload)
    db.commit()
    return {
        "workspace_participant_id": str(participant.workspace_participant_id),
        "app_user_id": str(participant.app_user_id),
        "participant_role": participant.participant_role.value,
    }


@router.get("/{workspace_id}/line-items")
def list_workspace_line_items(
    workspace_id: UUID,
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
    line_items = db.scalars(select(LineItem).where(LineItem.workspace_id == workspace_id).order_by(LineItem.created_at)).all()
    return [
        {
            "line_item_id": str(line_item.line_item_id),
            "line_item_key": line_item.line_item_key,
            "line_item_title": line_item.line_item_title,
            "line_item_status": line_item.line_item_status.value,
            "closed_reason": line_item.closed_reason,
        }
        for line_item in line_items
    ]


@router.post("/{workspace_id}/line-items", status_code=status.HTTP_201_CREATED)
def add_line_item_route(
    workspace_id: UUID,
    payload: LineItemCreateInput,
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    workspace = db.get(Workspace, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found.")
    authorize(session=db, user=current_user, required_roles=[RoleCode.ADMIN], access_group_id=workspace.access_group_id)
    line_item = add_line_item(db, actor=current_user, workspace_id=workspace.workspace_id, payload=payload)
    db.commit()
    return {
        "line_item_id": str(line_item.line_item_id),
        "line_item_key": line_item.line_item_key,
        "line_item_title": line_item.line_item_title,
        "line_item_status": line_item.line_item_status.value,
    }


@router.patch("/line-items/{line_item_id}")
def update_line_item_route(
    line_item_id: UUID,
    payload: LineItemUpdateRequest,
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
        required_roles=[RoleCode.ADMIN, RoleCode.REVIEWER],
        access_group_id=workspace.access_group_id,
        workspace_id=workspace.workspace_id,
        participant_roles=[ParticipantRole.ADMIN, ParticipantRole.REVIEWER],
    )
    update_line_item(line_item=line_item, payload=payload)
    db.commit()
    return {
        "line_item_id": str(line_item.line_item_id),
        "line_item_key": line_item.line_item_key,
        "line_item_title": line_item.line_item_title,
        "line_item_status": line_item.line_item_status.value,
        "closed_reason": line_item.closed_reason,
    }


@router.post("/{workspace_id}/status")
def change_workspace_status_route(
    workspace_id: UUID,
    payload: WorkspaceStatusChangeRequest,
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    workspace = db.get(Workspace, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found.")
    authorize(session=db, user=current_user, required_roles=[RoleCode.ADMIN], access_group_id=workspace.access_group_id)
    change_workspace_status(db, actor=current_user, workspace=workspace, payload=payload)
    db.commit()
    template = db.scalar(
        select(Template).options(selectinload(Template.field_definitions)).where(Template.template_id == workspace.template_id)
    )
    return serialize_workspace_detail(session=db, workspace=workspace, template=template, submitter_view=False)


@router.post("/{workspace_id}/line-items/{line_item_id}/payloads", status_code=status.HTTP_201_CREATED)
def save_line_item_payload(
    workspace_id: UUID,
    line_item_id: UUID,
    payload: PayloadSaveRequest,
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    workspace = db.get(Workspace, workspace_id)
    line_item = db.get(LineItem, line_item_id)
    if workspace is None or line_item is None or line_item.workspace_id != workspace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace or line item not found.")
    roles = set(
        authorize(
            session=db,
            user=current_user,
            required_roles=[RoleCode.SUBMITTER, RoleCode.REVIEWER, RoleCode.ADMIN],
            access_group_id=workspace.access_group_id,
            workspace_id=workspace.workspace_id,
            participant_roles=[ParticipantRole.SUBMITTER, ParticipantRole.REVIEWER, ParticipantRole.ADMIN],
        )
    )
    template = db.scalar(
        select(Template).options(selectinload(Template.field_definitions)).where(Template.template_id == workspace.template_id)
    )
    participant = db.scalar(
        select(WorkspaceParticipant).where(
            WorkspaceParticipant.workspace_id == workspace.workspace_id,
            WorkspaceParticipant.app_user_id == current_user.app_user_id,
            WorkspaceParticipant.removed_at.is_(None),
        )
    )
    revision, current_payload, issues = save_payload_revision(
        db,
        actor=current_user,
        workspace=workspace,
        line_item=line_item,
        template=template,
        payload=payload,
        actor_roles=roles,
        participant_role=participant.participant_role if participant else None,
    )
    db.commit()
    return {
        "workspace_revision_id": str(revision.workspace_revision_id),
        "revision_number": revision.revision_number,
        "current_payload_id": str(current_payload.current_payload_id),
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
        ],
    }


@router.get("/{workspace_id}/line-items/{line_item_id}/payloads/current")
def get_current_payload(
    workspace_id: UUID,
    line_item_id: UUID,
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
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
    payload = db.scalar(
        select(CurrentPayload).where(
            CurrentPayload.workspace_id == workspace.workspace_id,
            CurrentPayload.line_item_id == line_item_id,
            CurrentPayload.is_current.is_(True),
        )
    )
    if payload is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payload not found.")
    return {
        "current_payload_id": str(payload.current_payload_id),
        "workspace_revision_id": str(payload.workspace_revision_id),
        "payload_json": payload.payload_json,
        "payload_archived": payload.payload_archived,
        "payload_artifact_id": str(payload.payload_artifact_id) if payload.payload_artifact_id else None,
    }


@router.get("/{workspace_id}/revisions")
def list_workspace_revisions(
    workspace_id: UUID,
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
    revisions = db.scalars(
        select(WorkspaceRevision).where(WorkspaceRevision.workspace_id == workspace.workspace_id).order_by(
            WorkspaceRevision.revision_number.desc()
        )
    ).all()
    return [
        {
            "workspace_revision_id": str(revision.workspace_revision_id),
            "revision_number": revision.revision_number,
            "revision_reason": revision.revision_reason.value,
            "created_at": revision.created_at.isoformat(),
        }
        for revision in revisions
    ]


@router.get("/{workspace_id}/revisions/{revision_id}")
def get_workspace_revision_detail(
    workspace_id: UUID,
    revision_id: UUID,
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
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
    revision = db.get(WorkspaceRevision, revision_id)
    if revision is None or revision.workspace_id != workspace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Revision not found.")
    payloads = db.scalars(
        select(CurrentPayload).where(CurrentPayload.workspace_revision_id == revision_id).order_by(CurrentPayload.created_at)
    ).all()
    return {
        "workspace_revision_id": str(revision.workspace_revision_id),
        "revision_number": revision.revision_number,
        "revision_reason": revision.revision_reason.value,
        "created_at": revision.created_at.isoformat(),
        "payloads": [
            {
                "current_payload_id": str(item.current_payload_id),
                "line_item_id": str(item.line_item_id) if item.line_item_id else None,
                "payload_json": item.payload_json,
                "payload_archived": item.payload_archived,
                "payload_artifact_id": str(item.payload_artifact_id) if item.payload_artifact_id else None,
            }
            for item in payloads
        ],
    }
