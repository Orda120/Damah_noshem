from __future__ import annotations

from sqlalchemy import func, select

from app.db.models import CurrentPayload, FinalValue, LineItem, OutputBatchItem, ValidationIssue, Workspace
from app.db.session import SessionLocal

from conftest import login_as


def _seed_workspace_and_items():
    with SessionLocal() as session:
        workspace = session.scalar(select(Workspace).where(Workspace.workspace_title == "פיוס יומי 2026-04-08"))
        open_item = session.scalar(select(LineItem).where(LineItem.line_item_key == "LI-001"))
        done_item = session.scalar(select(LineItem).where(LineItem.line_item_key == "LI-002"))
        return workspace.workspace_id, open_item.line_item_id, done_item.line_item_id


def test_workspace_creation_invalid_participants_rolls_back(client):
    login_as(client, "admin", "admin123")
    with SessionLocal() as session:
        before = session.scalar(select(func.count(Workspace.workspace_id)))
        group_id = str(session.scalar(select(Workspace.access_group_id)))
        template_id = str(session.scalar(select(Workspace.template_id)))

    response = client.post(
        "/api/v1/workspaces",
        json={
            "access_group_id": group_id,
            "template_id": template_id,
            "workspace_title": "Should Fail",
            "participants": [{"app_user_id": "00000000-0000-0000-0000-000000000000", "participant_role": "submitter"}],
            "line_items": [{"line_item_key": "NEW-1", "line_item_title": "New item"}],
        },
    )
    assert response.status_code == 400
    with SessionLocal() as session:
        after = session.scalar(select(func.count(Workspace.workspace_id)))
        assert before == after


def test_stale_expected_revision_number_is_rejected(client):
    login_as(client, "admin", "admin123")
    workspace_id, open_item_id, _ = _seed_workspace_and_items()
    response = client.post(
        f"/api/v1/workspaces/{workspace_id}/line-items/{open_item_id}/payloads",
        json={
            "expected_revision_number": 99,
            "revision_reason": "admin_edit",
            "payload_json": {"reported_amount": 100, "approved_amount": 100},
        },
    )
    assert response.status_code == 409


def test_internal_only_comments_hidden_from_submitter(client):
    login_as(client, "submitter", "submitter123")
    workspace_id, _, _ = _seed_workspace_and_items()
    response = client.get(f"/api/v1/workspaces/{workspace_id}")
    assert response.status_code == 200
    comments = response.json()["comments"]
    assert all(comment["visibility_type"] != "internal_only" for comment in comments)


def test_done_is_blocked_when_blocking_issues_exist(client):
    login_as(client, "admin", "admin123")
    _, open_item_id, _ = _seed_workspace_and_items()
    response = client.post(
        f"/api/v1/line-items/{open_item_id}/finalize",
        json={"action": "done", "final_value_json": {"approved_amount": 1000}},
    )
    assert response.status_code == 400


def test_final_value_supersession_remains_append_only(client):
    login_as(client, "admin", "admin123")
    _, _, done_item_id = _seed_workspace_and_items()
    response = client.post(
        f"/api/v1/line-items/{done_item_id}/finalize",
        json={"action": "done", "final_value_json": {"approved_amount": 991}, "change_reason": "supersede"},
    )
    assert response.status_code == 200
    with SessionLocal() as session:
        values = session.scalars(
            select(FinalValue).where(FinalValue.line_item_id == done_item_id).order_by(FinalValue.approved_at)
        ).all()
        assert len(values) == 2
        assert len([value for value in values if value.is_current]) == 1
        assert any(value.superseded_at is not None for value in values)


def test_archive_stub_row_is_idempotent_and_keeps_row(client):
    login_as(client, "admin", "admin123")
    workspace_id, open_item_id, _ = _seed_workspace_and_items()
    with SessionLocal() as session:
        payload = session.scalar(
            select(CurrentPayload).where(CurrentPayload.workspace_id == workspace_id, CurrentPayload.line_item_id == open_item_id)
        )
        payload_id = payload.current_payload_id
    first = client.post(f"/api/v1/payloads/{payload_id}/archive", json={"snapshot_type": "monthly_archive"})
    second = client.post(f"/api/v1/payloads/{payload_id}/archive", json={"snapshot_type": "monthly_archive"})
    assert first.status_code == 200
    assert second.status_code == 200
    with SessionLocal() as session:
        refreshed = session.get(CurrentPayload, payload_id)
        assert refreshed is not None
        assert refreshed.payload_archived is True
        assert refreshed.payload_json is None
        assert refreshed.payload_artifact_id is not None


def test_output_generation_includes_only_done_items_with_current_final_values(client):
    login_as(client, "admin", "admin123")
    response = client.post("/api/v1/output/generate", json={"scope_type": "custom", "scope_ref": "all"})
    assert response.status_code == 200
    body = response.json()
    assert body["included_item_count"] >= 1
    with SessionLocal() as session:
        batch_items = session.scalars(select(OutputBatchItem)).all()
        assert len(batch_items) == body["included_item_count"]
