from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.enums import RoleCode
from app.db.models import AppUser, ArchiveCatalogEntry, ArchiveRestoreRequest, CurrentPayload, Workspace
from app.db.session import get_db
from app.schemas.api import ArchivePayloadRequest, RestoreRequest
from app.services.archive import archive_current_payload, record_restore_request
from app.services.authorization import authorize

router = APIRouter(tags=["archive"])


@router.post("/payloads/{current_payload_id}/archive")
def archive_payload_route(
    current_payload_id: UUID,
    payload: ArchivePayloadRequest,
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    current_payload = db.get(CurrentPayload, current_payload_id)
    if current_payload is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payload not found.")
    workspace = db.get(Workspace, current_payload.workspace_id)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found.")
    authorize(session=db, user=current_user, required_roles=[RoleCode.ADMIN], access_group_id=workspace.access_group_id)
    current_payload = archive_current_payload(
        db,
        actor=current_user,
        current_payload=current_payload,
        workspace=workspace,
        payload=payload,
    )
    db.commit()
    return {
        "current_payload_id": str(current_payload.current_payload_id),
        "payload_archived": current_payload.payload_archived,
        "payload_artifact_id": str(current_payload.payload_artifact_id) if current_payload.payload_artifact_id else None,
    }


@router.get("/archive/search")
def search_archive(
    access_group_id: UUID | None = None,
    workspace_id: UUID | None = None,
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    authorize(session=db, user=current_user, required_roles=[RoleCode.REVIEWER, RoleCode.ADMIN])
    query = select(ArchiveCatalogEntry)
    if access_group_id:
        query = query.where(ArchiveCatalogEntry.access_group_id == access_group_id)
    if workspace_id:
        query = query.where(ArchiveCatalogEntry.workspace_id == workspace_id)
    rows = db.scalars(query.order_by(ArchiveCatalogEntry.archived_at.desc())).all()
    return [
        {
            "archive_catalog_entry_id": str(entry.archive_catalog_entry_id),
            "artifact_id": str(entry.artifact_id),
            "workspace_id": str(entry.workspace_id) if entry.workspace_id else None,
            "line_item_id": str(entry.line_item_id) if entry.line_item_id else None,
            "artifact_type": entry.artifact_type.value,
            "archived_at": entry.archived_at.isoformat(),
            "retention_class": entry.retention_class,
        }
        for entry in rows
    ]


@router.get("/archive/entries/{archive_catalog_entry_id}")
def get_archive_entry(
    archive_catalog_entry_id: UUID,
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    authorize(session=db, user=current_user, required_roles=[RoleCode.REVIEWER, RoleCode.ADMIN])
    entry = db.get(ArchiveCatalogEntry, archive_catalog_entry_id)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Archive entry not found.")
    return {
        "archive_catalog_entry_id": str(entry.archive_catalog_entry_id),
        "artifact_id": str(entry.artifact_id),
        "workspace_id": str(entry.workspace_id) if entry.workspace_id else None,
        "line_item_id": str(entry.line_item_id) if entry.line_item_id else None,
        "template_id": str(entry.template_id) if entry.template_id else None,
        "workspace_revision_id": str(entry.workspace_revision_id) if entry.workspace_revision_id else None,
        "business_date": entry.business_date.isoformat() if entry.business_date else None,
        "access_group_id": str(entry.access_group_id) if entry.access_group_id else None,
        "status_at_archive_time": entry.status_at_archive_time,
        "artifact_type": entry.artifact_type.value,
        "archived_at": entry.archived_at.isoformat(),
        "retention_class": entry.retention_class,
    }


@router.post("/archive/restore-requests")
def restore_request_route(
    payload: RestoreRequest,
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    authorize(session=db, user=current_user, required_roles=[RoleCode.ADMIN])
    result = record_restore_request(db, actor=current_user, payload=payload)
    db.commit()
    return {
        "archive_restore_request_id": str(result.archive_restore_request_id),
        "archive_catalog_entry_id": str(result.archive_catalog_entry_id),
        "status": result.status.value,
        "requested_at": result.requested_at.isoformat(),
        "reason": result.reason,
    }


@router.get("/archive/restore-requests/{archive_restore_request_id}")
def get_restore_request_status(
    archive_restore_request_id: UUID,
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    authorize(session=db, user=current_user, required_roles=[RoleCode.ADMIN])
    restore_request = db.get(ArchiveRestoreRequest, archive_restore_request_id)
    if restore_request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restore request not found.")
    return {
        "archive_restore_request_id": str(restore_request.archive_restore_request_id),
        "archive_catalog_entry_id": str(restore_request.archive_catalog_entry_id),
        "status": restore_request.status.value,
        "requested_at": restore_request.requested_at.isoformat(),
        "completed_at": restore_request.completed_at.isoformat() if restore_request.completed_at else None,
        "reason": restore_request.reason,
        "failure_reason": restore_request.failure_reason,
    }
