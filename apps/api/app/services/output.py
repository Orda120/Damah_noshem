from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.db.enums import ArtifactType, LineItemStatus, OutputScopeType
from app.db.models import AppUser, Artifact, FinalValue, LineItem, OutputBatch, OutputBatchItem, Workspace
from app.schemas.api import OutputGenerateRequest
from app.services.audit import log_audit_event
from app.storage.factory import get_storage


def generate_output_batch(session: Session, *, actor: AppUser, payload: OutputGenerateRequest) -> OutputBatch:
    items_query: Select[tuple[LineItem, FinalValue, Workspace]] = (
        select(LineItem, FinalValue, Workspace)
        .join(FinalValue, FinalValue.line_item_id == LineItem.line_item_id)
        .join(Workspace, Workspace.workspace_id == LineItem.workspace_id)
        .where(FinalValue.is_current.is_(True), LineItem.line_item_status == LineItemStatus.DONE)
    )
    if payload.scope_type == OutputScopeType.GROUP:
        items_query = items_query.where(Workspace.access_group_id == payload.scope_ref)
    elif payload.scope_type == OutputScopeType.BUSINESS_DATE:
        items_query = items_query.where(Workspace.business_date == payload.scope_ref)

    rows = session.execute(items_query).all()
    output_batch = OutputBatch(
        scope_type=payload.scope_type,
        scope_ref=payload.scope_ref,
        generated_by_user_id=actor.app_user_id,
        included_item_count=len(rows),
        excluded_open_item_count=0,
        excluded_closed_item_count=0,
    )
    session.add(output_batch)
    session.flush()

    export_rows = []
    for line_item, final_value, workspace in rows:
        session.add(
            OutputBatchItem(
                output_batch_id=output_batch.output_batch_id,
                line_item_id=line_item.line_item_id,
                final_value_id=final_value.final_value_id,
            )
        )
        export_rows.append(
            {
                "workspace_id": str(workspace.workspace_id),
                "line_item_id": str(line_item.line_item_id),
                "line_item_key": line_item.line_item_key,
                "line_item_title": line_item.line_item_title,
                "final_value_json": final_value.final_value_json,
            }
        )

    storage = get_storage()
    payload_bytes = json.dumps(export_rows, ensure_ascii=False).encode("utf-8")
    stored = storage.write_bytes(
        relative_path=f"outputs/{output_batch.output_batch_id}.json",
        payload=payload_bytes,
    )
    artifact = Artifact(
        artifact_type=ArtifactType.EXPORT_EXCEL,
        storage_uri=stored.storage_uri,
        file_name=f"{output_batch.output_batch_id}.json",
        mime_type="application/json",
        checksum=stored.checksum,
        file_size_bytes=stored.file_size_bytes,
        created_by_user_id=actor.app_user_id,
        archived_at=None,
    )
    session.add(artifact)
    session.flush()
    output_batch.export_artifact_id = artifact.artifact_id
    output_batch.generated_at = datetime.now(UTC)
    log_audit_event(
        session,
        event_type="output_batch_generated",
        entity_type="output_batch",
        entity_id=output_batch.output_batch_id,
        actor_user=actor,
        payload={"included_item_count": len(rows)},
    )
    return output_batch
