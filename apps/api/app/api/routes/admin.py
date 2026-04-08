from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.db.enums import RoleCode
from app.db.models import AppUser, AuditEvent
from app.db.session import get_db
from app.schemas.serializers import serialize_audit_event
from app.services.authorization import authorize, get_user_roles

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/audit-events")
def list_audit_events(
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    authorize(session=db, user=current_user, required_roles=[RoleCode.ADMIN])
    events = db.scalars(select(AuditEvent).order_by(AuditEvent.created_at.desc())).all()
    return [serialize_audit_event(event) for event in events]


@router.get("/users")
def list_users(
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    authorize(session=db, user=current_user, required_roles=[RoleCode.ADMIN, RoleCode.GROUP_ADMIN])
    users = db.scalars(select(AppUser).options(selectinload(AppUser.company_person)).order_by(AppUser.created_at)).all()
    results = []
    for user in users:
        roles = [role.value for role, _, _ in get_user_roles(db, user_id=user.app_user_id)]
        results.append(
            {
                "app_user_id": str(user.app_user_id),
                "employee_number": user.company_person.employee_number,
                "full_name_he": user.company_person.full_name_he,
                "full_name_en": user.company_person.full_name_en,
                "email": user.company_person.email,
                "roles": roles,
                "default_language": user.default_language.value,
            }
        )
    return results
