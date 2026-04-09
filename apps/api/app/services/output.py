from __future__ import annotations

import json
from datetime import UTC, date, datetime

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.db.enums import ArtifactType, LineItemStatus, OutputScopeType
from app.db.models import AppUser, Artifact, FinalValue, LineItem, OutputBatch, OutputBatchItem, Workspace
from app.schemas.api import OutputGenerateRequest
from app.services.audit import log_audit_event
from app.storage.factory import get_storage


def _scoped_items_query(payload: OutputGenerateRequest) -> Select[tuple[LineItem, FinalValue, Workspace]]:
    items_query: Select[tuple[LineItem, FinalValue, Workspace]] = (
        select(LineItem, FinalValue, Workspace)
        .join(FinalValue, FinalValue.line_item_id == LineItem.line_item_id)
        .join(Workspace, Workspace.workspace_id == LineItem.workspace_id)
        .where(FinalValue.is_current.is_(True), LineItem.line_item_status == LineItemStatus.DONE)
    )
    if payload.scope_type == OutputScopeType.GROUP:
        items_query = items_query.where(Workspace.access_group_id == payload.scope_ref)
    elif payload.scope_type == OutputScopeType.BUSINESS_DATE:
        items_query = items_query.where(Workspace.business_date == date.fromisoformat(payload.scope_ref))
    return items_query


def _scope_workspace_ids_subquery(payload: OutputGenerateRequest):
    query = select(Workspace.workspace_id)
    if payload.scope_type == OutputScopeType.GROUP:
        query = query.where(Workspace.access_group_id == payload.scope_ref)
    elif payload.scope_type == OutputScopeType.BUSINESS_DATE:
        query = query.where(Workspace.business_date == date.fromisoformat(payload.scope_ref))
    return query.subquery()


def preview_output_rows(session: Session, *, payload: OutputGenerateRequest) -> dict:
    rows = session.execute(_scoped_items_query(payload)).all()
    scoped_workspaces = _scope_workspace_ids_subquery(payload)
    open_count = session.scalar(
        select(func.count(LineItem.line_item_id))
        .join(Workspace, Workspace.workspace_id == LineItem.workspace_id)
        .where(Workspace.workspace_id.in_(select(scoped_workspaces.c.workspace_id)), LineItem.line_item_status == LineItemStatus.OPEN)
    )
    closed_count = session.scalar(
        select(func.count(LineItem.line_item_id))
        .join(Workspace, Workspace.workspace_id == LineItem.workspace_id)
        .where(
            Workspace.workspace_id.in_(select(scoped_workspaces.c.workspace_id)),
            LineItem.line_item_status == LineItemStatus.CLOSED,
        )
    )
    items = [
        {
            "workspace_id": str(workspace.workspace_id),
            "line_item_id": str(line_item.line_item_id),
            "line_item_key": line_item.line_item_key,
            "line_item_title": line_item.line_item_title,
            "final_value_id": str(final_value.final_value_id),
            "final_value_json": final_value.final_value_json,
        }
        for line_item, final_value, workspace in rows
    ]
    return {
        "scope_type": payload.scope_type.value,
        "scope_ref": payload.scope_ref,
        "included_item_count": len(items),
        "excluded_open_item_count": open_count or 0,
        "excluded_closed_item_count": closed_count or 0,
        "items": items,
    }


def generate_output_batch(session: Session, *, actor: AppUser, payload: OutputGenerateRequest) -> OutputBatch:
    # Acquire FOR UPDATE lock first, then compute counts from locked data
    # to prevent stale counts from concurrent final-value supersession.
    rows = session.execute(_scoped_items_query(payload).with_for_update()).all()

    # Compute excluded counts under the same lock context.
    scoped_workspaces = _scope_workspace_ids_subquery(payload)
    excluded_open = session.scalar(
        select(func.count(LineItem.line_item_id))
        .join(Workspace, Workspace.workspace_id == LineItem.workspace_id)
        .where(
            Workspace.workspace_id.in_(select(scoped_workspaces.c.workspace_id)),
            LineItem.line_item_status == LineItemStatus.OPEN,
        )
    ) or 0
    excluded_closed = session.scalar(
        select(func.count(LineItem.line_item_id))
        .join(Workspace, Workspace.workspace_id == LineItem.workspace_id)
        .where(
            Workspace.workspace_id.in_(select(scoped_workspaces.c.workspace_id)),
            LineItem.line_item_status == LineItemStatus.CLOSED,
        )
    ) or 0

    output_batch = OutputBatch(
        scope_type=payload.scope_type,
        scope_ref=payload.scope_ref,
        generated_by_user_id=actor.app_user_id,
        included_item_count=len(rows),
        excluded_open_item_count=excluded_open,
        excluded_closed_item_count=excluded_closed,
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
                "final_value_id": str(final_value.final_value_id),
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
