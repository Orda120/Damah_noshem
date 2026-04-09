from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.enums import RoleCode
from app.db.models import AppUser, OutputBatch, OutputBatchItem
from app.db.session import get_db
from app.schemas.api import OutputGenerateRequest
from app.services.authorization import authorize
from app.services.output import generate_output_batch, preview_output_rows

router = APIRouter(prefix="/output", tags=["output"])


@router.post("/generate")
def generate_output(
    payload: OutputGenerateRequest,
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    authorize(session=db, user=current_user, required_roles=[RoleCode.ADMIN])
    batch = generate_output_batch(db, actor=current_user, payload=payload)
    db.commit()
    return {
        "output_batch_id": str(batch.output_batch_id),
        "scope_type": batch.scope_type.value,
        "scope_ref": batch.scope_ref,
        "included_item_count": batch.included_item_count,
        "export_artifact_id": str(batch.export_artifact_id) if batch.export_artifact_id else None,
    }


@router.post("/preview")
def preview_output(
    payload: OutputGenerateRequest,
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    authorize(session=db, user=current_user, required_roles=[RoleCode.ADMIN])
    return preview_output_rows(db, payload=payload)


@router.get("/batches")
def list_output_batches(
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    authorize(session=db, user=current_user, required_roles=[RoleCode.ADMIN])
    batches = db.scalars(select(OutputBatch).order_by(OutputBatch.generated_at.desc())).all()
    return [
        {
            "output_batch_id": str(batch.output_batch_id),
            "scope_type": batch.scope_type.value,
            "scope_ref": batch.scope_ref,
            "generated_at": batch.generated_at.isoformat(),
            "included_item_count": batch.included_item_count,
            "export_artifact_id": str(batch.export_artifact_id) if batch.export_artifact_id else None,
        }
        for batch in batches
    ]


@router.get("/batches/{output_batch_id}")
def get_output_batch(
    output_batch_id: UUID,
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    authorize(session=db, user=current_user, required_roles=[RoleCode.ADMIN])
    batch = db.get(OutputBatch, output_batch_id)
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Output batch not found.")
    return {
        "output_batch_id": str(batch.output_batch_id),
        "scope_type": batch.scope_type.value,
        "scope_ref": batch.scope_ref,
        "generated_at": batch.generated_at.isoformat(),
        "included_item_count": batch.included_item_count,
        "excluded_open_item_count": batch.excluded_open_item_count,
        "excluded_closed_item_count": batch.excluded_closed_item_count,
        "export_artifact_id": str(batch.export_artifact_id) if batch.export_artifact_id else None,
    }


@router.get("/batches/{output_batch_id}/items")
def list_output_batch_items(
    output_batch_id: UUID,
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    authorize(session=db, user=current_user, required_roles=[RoleCode.ADMIN])
    batch = db.get(OutputBatch, output_batch_id)
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Output batch not found.")
    items = db.scalars(
        select(OutputBatchItem).where(OutputBatchItem.output_batch_id == output_batch_id).order_by(OutputBatchItem.output_batch_item_id)
    ).all()
    return [
        {
            "output_batch_item_id": str(item.output_batch_item_id),
            "line_item_id": str(item.line_item_id),
            "final_value_id": str(item.final_value_id),
        }
        for item in items
    ]
