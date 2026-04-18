from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import AppUser, AuditEvent


def log_audit_event(
    session: Session,
    *,
    event_type: str,
    entity_type: str,
    entity_id: UUID | None,
    actor_user: AppUser | None,
    payload: dict | None = None,
) -> AuditEvent:
    event = AuditEvent(
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        actor_user_id=actor_user.app_user_id if actor_user else None,
        company_person_id=actor_user.company_person_id if actor_user else None,
        event_payload_json=payload or {},
    )
    session.add(event)
    session.flush()
    return event
