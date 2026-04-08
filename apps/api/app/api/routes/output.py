from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.enums import RoleCode
from app.db.models import AppUser, OutputBatch
from app.db.session import get_db
from app.schemas.api import OutputGenerateRequest
from app.services.authorization import authorize
from app.services.output import generate_output_batch

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
