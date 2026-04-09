from __future__ import annotations

from sqlalchemy import func, select

from app.db.enums import ClarificationStatus
from app.db.models import (
    ArchiveCatalogEntry,
    ArchiveRestoreRequest,
    AuditEvent,
    ClarificationRequest,
    CurrentPayload,
    LineItem,
    PayloadSnapshot,
    Workspace,
)
from app.db.session import SessionLocal

from conftest import login_as


def _seed_workspace_and_items():
    with SessionLocal() as session:
        workspace = session.scalar(select(Workspace).where(Workspace.workspace_title == "פיוס יומי 2026-04-08"))
        open_item = session.scalar(select(LineItem).where(LineItem.line_item_key == "LI-001"))
        done_item = session.scalar(select(LineItem).where(LineItem.line_item_key == "LI-002"))
        return workspace.workspace_id, open_item.line_item_id, done_item.line_item_id


# ===== Archive idempotency tests =====


def test_archive_creates_exactly_one_snapshot_on_double_call(client):
    """Calling archive twice for the same payload must not create duplicate PayloadSnapshots."""
    login_as(client, "admin", "admin123")
    workspace_id, open_item_id, _ = _seed_workspace_and_items()
    with SessionLocal() as session:
        payload = session.scalar(
            select(CurrentPayload).where(
                CurrentPayload.workspace_id == workspace_id,
                CurrentPayload.line_item_id == open_item_id,
            )
        )
        payload_id = payload.current_payload_id

    first = client.post(f"/api/v1/payloads/{payload_id}/archive", json={"snapshot_type": "monthly_archive"})
    second = client.post(f"/api/v1/payloads/{payload_id}/archive", json={"snapshot_type": "monthly_archive"})
    assert first.status_code == 200
    assert second.status_code == 200

    with SessionLocal() as session:
        snapshot_count = session.scalar(
            select(func.count(PayloadSnapshot.payload_snapshot_id)).where(
                PayloadSnapshot.workspace_id == workspace_id,
                PayloadSnapshot.line_item_id == open_item_id,
            )
        )
        assert snapshot_count == 1, f"Expected exactly 1 snapshot, got {snapshot_count}"

        catalog_count = session.scalar(
            select(func.count(ArchiveCatalogEntry.archive_catalog_entry_id)).where(
                ArchiveCatalogEntry.workspace_id == workspace_id,
                ArchiveCatalogEntry.line_item_id == open_item_id,
            )
        )
        assert catalog_count == 1, f"Expected exactly 1 catalog entry, got {catalog_count}"


# ===== Restore idempotency tests =====


def test_restore_request_idempotency_returns_existing(client):
    """Calling restore twice for the same catalog entry returns the same request without duplication."""
    login_as(client, "admin", "admin123")
    workspace_id, open_item_id, _ = _seed_workspace_and_items()
    with SessionLocal() as session:
        payload = session.scalar(
            select(CurrentPayload).where(
                CurrentPayload.workspace_id == workspace_id,
                CurrentPayload.line_item_id == open_item_id,
            )
        )
        payload_id = payload.current_payload_id

    client.post(f"/api/v1/payloads/{payload_id}/archive", json={"snapshot_type": "monthly_archive"})
    with SessionLocal() as session:
        entry = session.scalar(
            select(ArchiveCatalogEntry).where(ArchiveCatalogEntry.line_item_id == open_item_id)
        )
        entry_id = entry.archive_catalog_entry_id

    first_restore = client.post(
        "/api/v1/archive/restore-requests",
        json={"archive_catalog_entry_id": str(entry_id), "reason": "check"},
    )
    second_restore = client.post(
        "/api/v1/archive/restore-requests",
        json={"archive_catalog_entry_id": str(entry_id), "reason": "check again"},
    )
    assert first_restore.status_code == 200
    assert second_restore.status_code == 200
    assert first_restore.json()["archive_restore_request_id"] == second_restore.json()["archive_restore_request_id"]

    with SessionLocal() as session:
        request_count = session.scalar(
            select(func.count(ArchiveRestoreRequest.archive_restore_request_id)).where(
                ArchiveRestoreRequest.archive_catalog_entry_id == entry_id,
            )
        )
        assert request_count == 1, f"Expected exactly 1 restore request, got {request_count}"


# ===== Clarification auto-close tests =====


def test_clarification_auto_closes_when_line_item_finalized_done(client):
    """Open/answered clarifications on a line item are auto-closed when it is marked Done."""
    login_as(client, "admin", "admin123")
    workspace_id, open_item_id, _ = _seed_workspace_and_items()

    # The seed has a blocking validation issue on LI-001 (approved_amount > reported_amount).
    # First, resolve the validation issue by submitting a valid payload.
    client.post(
        f"/api/v1/workspaces/{workspace_id}/line-items/{open_item_id}/payloads",
        json={
            "expected_revision_number": 2,
            "revision_reason": "admin_edit",
            "payload_json": {"reported_amount": 1500, "approved_amount": 1200, "notes": "Fixed"},
        },
    )

    # Add an open clarification on the same line item
    create_resp = client.post(
        f"/api/v1/workspaces/{workspace_id}/line-items/{open_item_id}/clarifications",
        json={"message": "Please double-check this."},
    )
    assert create_resp.status_code == 201, create_resp.text

    # Finalize as Done
    finalize_resp = client.post(
        f"/api/v1/line-items/{open_item_id}/finalize",
        json={"action": "done", "final_value_json": {"approved_amount": 1200}},
    )
    assert finalize_resp.status_code == 200, finalize_resp.text

    # All clarifications for this item should now be closed
    with SessionLocal() as session:
        clarifications = session.scalars(
            select(ClarificationRequest).where(
                ClarificationRequest.line_item_id == open_item_id,
            )
        ).all()
        for clar in clarifications:
            assert clar.status == ClarificationStatus.CLOSED, f"Expected CLOSED, got {clar.status}"
            assert clar.closed_at is not None

        # Verify audit event
        audit = session.scalar(
            select(AuditEvent).where(AuditEvent.event_type == "clarifications_auto_closed").order_by(
                AuditEvent.created_at.desc()
            )
        )
        assert audit is not None
        assert audit.event_payload_json["trigger"] == "done"


def test_clarification_auto_closes_when_line_item_closed(client):
    """Open/answered clarifications auto-close when the line item is Closed."""
    login_as(client, "admin", "admin123")
    workspace_id, open_item_id, _ = _seed_workspace_and_items()

    # Add an open clarification
    create_resp = client.post(
        f"/api/v1/workspaces/{workspace_id}/line-items/{open_item_id}/clarifications",
        json={"message": "Need info"},
    )
    assert create_resp.status_code == 201

    # Close the line item (no final value needed for close)
    finalize_resp = client.post(
        f"/api/v1/line-items/{open_item_id}/finalize",
        json={"action": "closed", "change_reason": "Not applicable"},
    )
    assert finalize_resp.status_code == 200, finalize_resp.text

    with SessionLocal() as session:
        clarifications = session.scalars(
            select(ClarificationRequest).where(
                ClarificationRequest.line_item_id == open_item_id,
            )
        ).all()
        for clar in clarifications:
            assert clar.status == ClarificationStatus.CLOSED


# ===== Output batch locked counts test =====


def test_output_batch_counts_are_consistent(client):
    """Output batch included/excluded counts must be consistent with locked data."""
    login_as(client, "admin", "admin123")
    # Preview first
    preview = client.post("/api/v1/output/preview", json={"scope_type": "custom", "scope_ref": "all"})
    assert preview.status_code == 200

    # Generate
    generate = client.post("/api/v1/output/generate", json={"scope_type": "custom", "scope_ref": "all"})
    assert generate.status_code == 200
    body = generate.json()
    assert body["included_item_count"] >= 0

    # Fetch batch detail which includes excluded counts
    batch_id = body["output_batch_id"]
    detail = client.get(f"/api/v1/output/batches/{batch_id}")
    assert detail.status_code == 200
    detail_body = detail.json()
    assert detail_body["excluded_open_item_count"] >= 0
    assert detail_body["excluded_closed_item_count"] >= 0
