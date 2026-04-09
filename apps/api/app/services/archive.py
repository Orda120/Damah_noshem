from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.enums import ArtifactEntityType, ArtifactLinkRole, ArtifactType, RestoreStatus, SnapshotType
from app.db.models import (
    ArchiveCatalogEntry,
    ArchiveRestoreRequest,
    AppUser,
    Artifact,
    ArtifactLink,
    CurrentPayload,
    LineItem,
    PayloadSnapshot,
    Workspace,
)
from app.schemas.api import ArchivePayloadRequest, RestoreRequest
from app.services.audit import log_audit_event
from app.storage.factory import get_storage


def archive_current_payload(
    session: Session,
    *,
    actor: AppUser,
    current_payload: CurrentPayload,
    workspace: Workspace,
    payload: ArchivePayloadRequest,
) -> CurrentPayload:
    # ---- idempotency: already fully archived ----
    if current_payload.payload_archived and current_payload.payload_artifact_id:
        return current_payload
    if current_payload.payload_json is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payload body is empty.")

    # ---- idempotency: check for a prior partial run that created a snapshot ----
    existing_snapshot = session.scalar(
        select(PayloadSnapshot).where(
            PayloadSnapshot.workspace_id == current_payload.workspace_id,
            PayloadSnapshot.line_item_id == current_payload.line_item_id,
            PayloadSnapshot.workspace_revision_id == current_payload.workspace_revision_id,
        )
    )
    if existing_snapshot is not None:
        # A previous attempt already wrote the artifact + snapshot.
        # Verify checksum to guard against corrupted partial writes.
        existing_artifact = session.get(Artifact, existing_snapshot.artifact_id)
        serialized = json.dumps(current_payload.payload_json, ensure_ascii=False).encode("utf-8")
        expected_checksum = hashlib.sha256(serialized).hexdigest()
        if existing_artifact is not None and existing_artifact.checksum == expected_checksum:
            # Re-apply the stub transition that may have failed previously.
            current_payload.payload_json = None
            current_payload.payload_archived = True
            current_payload.payload_artifact_id = existing_artifact.artifact_id
            current_payload.archived_at = current_payload.archived_at or datetime.now(UTC)
            return current_payload
        # Checksum mismatch — fall through to re-archive to correct the inconsistency.

    line_item = session.get(LineItem, current_payload.line_item_id) if current_payload.line_item_id else None
    serialized = json.dumps(current_payload.payload_json, ensure_ascii=False).encode("utf-8")
    storage = get_storage()
    stored = storage.write_bytes(
        relative_path=f"payloads/{workspace.workspace_id}/{current_payload.current_payload_id}.json",
        payload=serialized,
    )
    artifact = Artifact(
        artifact_type=ArtifactType.PAYLOAD_SNAPSHOT,
        storage_uri=stored.storage_uri,
        file_name=f"{current_payload.current_payload_id}.json",
        mime_type="application/json",
        checksum=stored.checksum,
        file_size_bytes=stored.file_size_bytes,
        created_by_user_id=actor.app_user_id,
    )
    session.add(artifact)
    session.flush()

    snapshot = PayloadSnapshot(
        workspace_id=current_payload.workspace_id,
        line_item_id=current_payload.line_item_id,
        workspace_revision_id=current_payload.workspace_revision_id,
        artifact_id=artifact.artifact_id,
        snapshot_type=SnapshotType(payload.snapshot_type),
        created_by_user_id=actor.app_user_id,
    )
    session.add(snapshot)
    session.flush()
    session.add(
        ArtifactLink(
            artifact_id=artifact.artifact_id,
            entity_type=ArtifactEntityType.PAYLOAD_SNAPSHOT,
            entity_id=snapshot.payload_snapshot_id,
            link_role=ArtifactLinkRole.ARCHIVE_SNAPSHOT,
            linked_by_user_id=actor.app_user_id,
        )
    )
    session.flush()

    # ---- idempotency: avoid duplicate catalog entries ----
    existing_catalog = session.scalar(
        select(ArchiveCatalogEntry).where(
            ArchiveCatalogEntry.artifact_id == artifact.artifact_id,
            ArchiveCatalogEntry.workspace_id == current_payload.workspace_id,
            ArchiveCatalogEntry.line_item_id == current_payload.line_item_id,
        )
    )
    if existing_catalog is None:
        session.add(
            ArchiveCatalogEntry(
                artifact_id=artifact.artifact_id,
                workspace_id=current_payload.workspace_id,
                line_item_id=current_payload.line_item_id,
                template_id=current_payload.template_id,
                workspace_revision_id=current_payload.workspace_revision_id,
                business_date=workspace.business_date,
                access_group_id=workspace.access_group_id,
                status_at_archive_time=line_item.line_item_status.value if line_item else workspace.workspace_status.value,
                artifact_type=ArtifactType.PAYLOAD_SNAPSHOT,
                retention_class=payload.retention_class,
            )
        )

    current_payload.payload_json = None
    current_payload.payload_archived = True
    current_payload.payload_artifact_id = artifact.artifact_id
    current_payload.archived_at = datetime.now(UTC)
    log_audit_event(
        session,
        event_type="payload_archived",
        entity_type="current_payload",
        entity_id=current_payload.current_payload_id,
        actor_user=actor,
        payload={"artifact_id": str(artifact.artifact_id)},
    )
    return current_payload


def record_restore_request(
    session: Session,
    *,
    actor: AppUser,
    payload: RestoreRequest,
) -> ArchiveRestoreRequest:
    # ---- idempotency: return existing pending request ----
    existing = session.scalar(
        select(ArchiveRestoreRequest).where(
            ArchiveRestoreRequest.archive_catalog_entry_id == payload.archive_catalog_entry_id,
            ArchiveRestoreRequest.status == RestoreStatus.REQUESTED,
        )
    )
    if existing is not None:
        return existing

    restore_request = ArchiveRestoreRequest(
        archive_catalog_entry_id=payload.archive_catalog_entry_id,
        requested_by_user_id=actor.app_user_id,
        status=RestoreStatus.REQUESTED,
        reason=payload.reason,
    )
    session.add(restore_request)
    session.flush()
    log_audit_event(
        session,
        event_type="archive_restore_requested",
        entity_type="archive_catalog_entry",
        entity_id=payload.archive_catalog_entry_id,
        actor_user=actor,
        payload={"reason": payload.reason, "archive_restore_request_id": str(restore_request.archive_restore_request_id)},
    )
    return restore_request
