from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.db.enums import RoleCode
from app.db.models import AppUser, Template
from app.db.session import get_db
from app.schemas.api import TemplateCreateRequest, TemplateUpdateRequest
from app.schemas.serializers import serialize_template
from app.services.authorization import authorize
from app.services.workflow import create_template, update_template

router = APIRouter(prefix="/templates", tags=["templates"])


@router.get("")
def list_templates(current_user: AppUser = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict]:
    authorize(session=db, user=current_user, required_roles=[])
    templates = db.scalars(
        select(Template).options(selectinload(Template.field_definitions)).order_by(Template.template_code)
    ).all()
    return [serialize_template(template) for template in templates]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_template_route(
    payload: TemplateCreateRequest,
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    authorize(session=db, user=current_user, required_roles=[RoleCode.ADMIN])
    template = create_template(db, actor=current_user, payload=payload)
    db.commit()
    db.refresh(template)
    return serialize_template(template)


@router.get("/{template_id}")
def get_template(
    template_id: UUID,
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    authorize(session=db, user=current_user, required_roles=[])
    template = db.scalar(
        select(Template).options(selectinload(Template.field_definitions)).where(Template.template_id == template_id)
    )
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found.")
    return serialize_template(template)


@router.put("/{template_id}")
def update_template_route(
    template_id: UUID,
    payload: TemplateUpdateRequest,
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    authorize(session=db, user=current_user, required_roles=[RoleCode.ADMIN])
    template = db.scalar(
        select(Template).options(selectinload(Template.field_definitions)).where(Template.template_id == template_id)
    )
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found.")
    update_template(db, actor=current_user, template=template, payload=payload)
    db.commit()
    db.refresh(template)
    return serialize_template(template)
