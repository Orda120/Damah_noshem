from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.enums import ArtifactEntityType, ArtifactLinkRole, ArtifactType, RoleCode
from app.db.models import AppUser, Artifact, ArtifactLink
from app.db.session import get_db
from app.services.audit import log_audit_event
from app.services.authorization import authorize
from app.storage.factory import get_storage

router = APIRouter(prefix="/artifacts", tags=["artifacts"])


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_artifact(
    entity_type: ArtifactEntityType = Form(...),
    entity_id: str = Form(...),
    link_role: ArtifactLinkRole = Form(...),
    artifact_type: ArtifactType = Form(default=ArtifactType.OTHER),
    file: UploadFile = File(...),
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    authorize(session=db, user=current_user, required_roles=[RoleCode.REVIEWER, RoleCode.ADMIN, RoleCode.SUBMITTER])
    payload = await file.read()
    storage = get_storage()
    relative_path = f"uploads/{secrets.token_hex(8)}-{file.filename}"
    stored = storage.write_bytes(relative_path=relative_path, payload=payload)
    artifact = Artifact(
        artifact_type=artifact_type,
        storage_uri=stored.storage_uri,
        file_name=file.filename,
        mime_type=file.content_type or "application/octet-stream",
        checksum=stored.checksum,
        file_size_bytes=stored.file_size_bytes,
        created_by_user_id=current_user.app_user_id,
    )
    db.add(artifact)
    db.flush()
    link = ArtifactLink(
        artifact_id=artifact.artifact_id,
        entity_type=entity_type,
        entity_id=entity_id,
        link_role=link_role,
        linked_by_user_id=current_user.app_user_id,
    )
    db.add(link)
    log_audit_event(
        db,
        event_type="artifact_uploaded",
        entity_type="artifact",
        entity_id=artifact.artifact_id,
        actor_user=current_user,
        payload={"file_name": file.filename},
    )
    log_audit_event(
        db,
        event_type="artifact_linked",
        entity_type="artifact_link",
        entity_id=link.artifact_link_id,
        actor_user=current_user,
        payload={"entity_type": entity_type.value, "entity_id": entity_id},
    )
    db.commit()
    return {
        "artifact_id": str(artifact.artifact_id),
        "artifact_type": artifact.artifact_type.value,
        "storage_uri": artifact.storage_uri,
        "entity_type": link.entity_type.value,
        "entity_id": str(link.entity_id),
        "link_role": link.link_role.value,
    }


@router.get("")
def list_artifacts(
    entity_type: ArtifactEntityType,
    entity_id: str,
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    authorize(session=db, user=current_user, required_roles=[])
    rows = db.execute(
        select(Artifact, ArtifactLink)
        .join(ArtifactLink, ArtifactLink.artifact_id == Artifact.artifact_id)
        .where(ArtifactLink.entity_type == entity_type, ArtifactLink.entity_id == entity_id)
        .order_by(Artifact.created_at.desc())
    ).all()
    return [
        {
            "artifact_id": str(artifact.artifact_id),
            "artifact_type": artifact.artifact_type.value,
            "file_name": artifact.file_name,
            "mime_type": artifact.mime_type,
            "storage_uri": artifact.storage_uri,
            "link_role": link.link_role.value,
        }
        for artifact, link in rows
    ]
