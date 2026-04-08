from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.enums import ArtifactEntityType, ArtifactLinkRole, ArtifactType, SnapshotType
from app.db.models import ArchiveCatalogEntry, AppUser, Artifact, ArtifactLink, CurrentPayload, PayloadSnapshot, Workspace
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
    if current_payload.payload_archived and current_payload.payload_artifact_id:
        return current_payload
    if current_payload.payload_json is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payload body is empty.")

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
    session.add(
        ArchiveCatalogEntry(
            artifact_id=artifact.artifact_id,
            workspace_id=current_payload.workspace_id,
            line_item_id=current_payload.line_item_id,
            template_id=current_payload.template_id,
            workspace_revision_id=current_payload.workspace_revision_id,
            business_date=workspace.business_date,
            access_group_id=workspace.access_group_id,
            status_at_archive_time=None,
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
) -> dict[str, str]:
    log_audit_event(
        session,
        event_type="archive_restore_requested",
        entity_type="archive_catalog_entry",
        entity_id=payload.archive_catalog_entry_id,
        actor_user=actor,
        payload={"reason": payload.reason},
    )
    return {"status": "requested"}
