from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.enums import (
    ArtifactEntityType,
    ArtifactLinkRole,
    ArtifactType,
    CommentVisibilityType,
    FieldType,
    LanguageCode,
    LineItemStatus,
    MembershipRole,
    OutputScopeType,
    ParticipantRole,
    RecommendedAction,
    RestoreStatus,
    RevisionReason,
    RoleCode,
    ScopeType,
    TemplateStatus,
    WorkspaceStatus,
)


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LoginPasswordRequest(ApiModel):
    username: str
    password: str


class SsoLoginStartRequest(ApiModel):
    provider: str = "stub"


class SsoLoginCallbackRequest(ApiModel):
    provider: str = "stub"
    external_subject: str
    email: str


class IdentityLinkRequest(ApiModel):
    provider: str = "stub"
    external_subject: str
    email: str
    username: str
    password: str


class PreferencesUpdateRequest(ApiModel):
    default_language: LanguageCode


class AccessCodeIssueRequest(ApiModel):
    expires_at: datetime | None = None
    max_uses: int = 1
    issued_for_scope: str | None = None


class GroupCreateRequest(ApiModel):
    group_name: str
    group_description: str | None = None
    access_code: str


class MembershipGrantRequest(ApiModel):
    app_user_id: UUID
    membership_role: MembershipRole = MembershipRole.MEMBER


class MembershipRoleUpdateRequest(ApiModel):
    membership_role: MembershipRole


class TemplateFieldDefinitionInput(ApiModel):
    field_key: str
    field_label_he: str
    field_label_en: str
    field_type: FieldType
    is_required: bool = False
    is_conditionally_required: bool = False
    submitter_editable: bool = True
    reviewer_editable: bool = False
    admin_editable: bool = True
    lock_on_done: bool = True
    lock_on_closed: bool = True
    display_order: int = 0
    validation_rule_ref: str | None = None


class TemplateCreateRequest(ApiModel):
    template_code: str
    template_name_he: str
    template_name_en: str
    template_status: TemplateStatus = TemplateStatus.DRAFT
    field_definitions: list[TemplateFieldDefinitionInput]


class TemplateUpdateRequest(ApiModel):
    template_name_he: str | None = None
    template_name_en: str | None = None
    template_status: TemplateStatus | None = None
    field_definitions: list[TemplateFieldDefinitionInput] | None = None


class ParticipantInput(ApiModel):
    app_user_id: UUID
    participant_role: ParticipantRole


class LineItemCreateInput(ApiModel):
    line_item_key: str
    line_item_title: str


class WorkspaceCreateRequest(ApiModel):
    access_group_id: UUID
    template_id: UUID
    workspace_title: str
    business_date: date | None = None
    participants: list[ParticipantInput] = Field(default_factory=list)
    line_items: list[LineItemCreateInput] = Field(default_factory=list)


class WorkspaceStatusChangeRequest(ApiModel):
    workspace_status: WorkspaceStatus
    change_reason: str | None = None


class WorkspaceUpdateRequest(ApiModel):
    workspace_title: str | None = None
    business_date: date | None = None


class PayloadSaveRequest(ApiModel):
    expected_revision_number: int
    payload_json: dict
    revision_reason: RevisionReason


class LineItemUpdateRequest(ApiModel):
    line_item_title: str | None = None
    line_item_status: LineItemStatus | None = None
    closed_reason: str | None = None


class CommentCreateRequest(ApiModel):
    comment_text: str
    visibility_type: CommentVisibilityType = CommentVisibilityType.SUBMITTER_VISIBLE
    clarification_request_id: UUID | None = None


class ClarificationCreateRequest(ApiModel):
    message: str


class ClarificationAnswerRequest(ApiModel):
    answer_text: str
    visibility_type: CommentVisibilityType = CommentVisibilityType.SUBMITTER_VISIBLE


class RecommendationCreateRequest(ApiModel):
    recommended_action: RecommendedAction
    recommended_final_value_json: dict | None = None
    reason_text: str | None = None


class LineItemFinalizeRequest(ApiModel):
    action: LineItemStatus
    final_value_json: dict | None = None
    override_reason: str | None = None
    change_reason: str | None = None


class ValidationResolveRequest(ApiModel):
    resolution_note: str | None = None


class OutputGenerateRequest(ApiModel):
    scope_type: OutputScopeType
    scope_ref: str


class ArchivePayloadRequest(ApiModel):
    snapshot_type: str = "monthly_archive"
    retention_class: str | None = None


class RestoreRequest(ApiModel):
    archive_catalog_entry_id: UUID
    reason: str | None = None


class RestoreStatusResponse(ApiModel):
    archive_restore_request_id: UUID
    archive_catalog_entry_id: UUID
    status: RestoreStatus
    requested_at: datetime
    completed_at: datetime | None = None
    reason: str | None = None


class UserPatchRequest(ApiModel):
    is_enabled: bool | None = None
    is_locked: bool | None = None


class RoleGrantRequest(ApiModel):
    role_code: RoleCode
    scope_type: ScopeType = ScopeType.GLOBAL
    scope_id: UUID | None = None
    failure_reason: str | None = None


class ArtifactLinkRequest(ApiModel):
    artifact_id: UUID
    entity_type: ArtifactEntityType
    entity_id: UUID
    link_role: ArtifactLinkRole


class MeResponse(ApiModel):
    app_user_id: UUID
    employee_number: str
    full_name_he: str
    full_name_en: str
    email: str
    default_language: LanguageCode
    roles: list[str]
    session_token: str | None = None


class ArtifactUploadResponse(ApiModel):
    artifact_id: UUID
    entity_type: ArtifactEntityType
    entity_id: UUID
    link_role: ArtifactLinkRole
    artifact_type: ArtifactType
