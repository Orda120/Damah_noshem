from __future__ import annotations

import os
import uuid
from datetime import UTC, date, datetime

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import expression
from sqlalchemy.types import Uuid

from app.db.base import Base
from app.db.enums import (
    AccessCodeType,
    AccessDecisionType,
    ArtifactEntityType,
    ArtifactLinkRole,
    ArtifactType,
    AttemptStatus,
    AuthType,
    ClarificationStatus,
    CommentVisibilityType,
    FieldType,
    GroupStatus,
    LanguageCode,
    LineItemStatus,
    MembershipRole,
    MembershipStatus,
    OutputScopeType,
    ParticipantRole,
    RecommendedAction,
    RevisionReason,
    RoleCode,
    RestoreStatus,
    ScopeType,
    SnapshotType,
    TemplateStatus,
    ValidationSeverity,
    ValidationStatus,
    WorkspaceStatus,
)

ARCHIVE_SCHEMA = os.getenv("ARCHIVE_SCHEMA", "archive_catalog")
JSON_VARIANT = MutableDict.as_mutable(JSON().with_variant(JSONB, "postgresql"))


def utcnow() -> datetime:
    return datetime.now(UTC)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class CompanyPerson(TimestampMixin, Base):
    __tablename__ = "company_person"

    company_person_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    employee_number: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    full_name_he: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name_en: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    department: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    app_user: Mapped["AppUser"] = relationship(back_populates="company_person", uselist=False)


class AppUser(TimestampMixin, Base):
    __tablename__ = "app_user"

    app_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    company_person_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("company_person.company_person_id"), unique=True, nullable=False
    )
    default_language: Mapped[LanguageCode] = mapped_column(
        Enum(LanguageCode, native_enum=False), default=LanguageCode.HE, nullable=False
    )
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    company_person: Mapped[CompanyPerson] = relationship(back_populates="app_user")
    auth_identities: Mapped[list["AuthIdentity"]] = relationship(back_populates="app_user")
    role_assignments: Mapped[list["UserRoleAssignment"]] = relationship(
        back_populates="app_user",
        foreign_keys="UserRoleAssignment.app_user_id",
    )


class AuthIdentity(Base):
    __tablename__ = "auth_identity"

    auth_identity_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    app_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.app_user_id"), nullable=False)
    auth_type: Mapped[AuthType] = mapped_column(
        Enum(AuthType, native_enum=False), default=AuthType.USERNAME_PASSWORD, nullable=False
    )
    external_subject: Mapped[str | None] = mapped_column(String(255))
    username: Mapped[str | None] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    is_primary: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    app_user: Mapped[AppUser] = relationship(back_populates="auth_identities")


class Role(Base):
    __tablename__ = "role"

    role_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    role_code: Mapped[RoleCode] = mapped_column(Enum(RoleCode, native_enum=False), unique=True, nullable=False)
    display_name_he: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name_en: Mapped[str] = mapped_column(String(255), nullable=False)
    is_system_role: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class UserRoleAssignment(Base):
    __tablename__ = "user_role_assignment"

    user_role_assignment_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    app_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.app_user_id"), nullable=False)
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("role.role_id"), nullable=False)
    scope_type: Mapped[ScopeType] = mapped_column(
        Enum(ScopeType, native_enum=False), default=ScopeType.GLOBAL, nullable=False
    )
    scope_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    granted_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.app_user_id"))
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.app_user_id"))

    app_user: Mapped[AppUser] = relationship(foreign_keys=[app_user_id], back_populates="role_assignments")
    role: Mapped[Role] = relationship()


class AccessCode(Base):
    __tablename__ = "access_code"

    access_code_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    code_value_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    code_type: Mapped[AccessCodeType] = mapped_column(
        Enum(AccessCodeType, native_enum=False), default=AccessCodeType.GROUP_CREATION, nullable=False
    )
    issued_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.app_user_id"))
    issued_for_scope: Mapped[str | None] = mapped_column(String(255))
    max_uses: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    use_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AccessGroup(TimestampMixin, Base):
    __tablename__ = "access_group"

    access_group_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    group_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    group_description: Mapped[str | None] = mapped_column(Text)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.app_user_id"))
    group_status: Mapped[GroupStatus] = mapped_column(
        Enum(GroupStatus, native_enum=False), default=GroupStatus.ACTIVE, nullable=False
    )


class GroupCreationEvent(Base):
    __tablename__ = "group_creation_event"

    group_creation_event_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    access_code_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("access_code.access_code_id"))
    created_group_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("access_group.access_group_id"))
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.app_user_id"), nullable=False)
    attempt_status: Mapped[AttemptStatus] = mapped_column(Enum(AttemptStatus, native_enum=False), nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class GroupMembership(Base):
    __tablename__ = "group_membership"
    __table_args__ = (
        UniqueConstraint("access_group_id", "app_user_id", "membership_status", name="uq_group_membership_state"),
    )

    group_membership_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    access_group_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("access_group.access_group_id"), nullable=False)
    app_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.app_user_id"), nullable=False)
    membership_role: Mapped[MembershipRole] = mapped_column(Enum(MembershipRole, native_enum=False), nullable=False)
    membership_status: Mapped[MembershipStatus] = mapped_column(
        Enum(MembershipStatus, native_enum=False), default=MembershipStatus.ACTIVE, nullable=False
    )
    granted_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.app_user_id"))
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    revoked_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.app_user_id"))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revocation_reason: Mapped[str | None] = mapped_column(Text)


class AccessPolicyDecision(Base):
    __tablename__ = "access_policy_decision"

    access_policy_decision_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    app_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.app_user_id"))
    company_person_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("company_person.company_person_id"))
    source_system: Mapped[str] = mapped_column(String(255), nullable=False)
    decision_type: Mapped[AccessDecisionType] = mapped_column(
        Enum(AccessDecisionType, native_enum=False), nullable=False
    )
    decision_reason: Mapped[str | None] = mapped_column(Text)
    decision_payload_ref: Mapped[str | None] = mapped_column(String(255))
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Template(TimestampMixin, Base):
    __tablename__ = "template"

    template_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    template_code: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    template_name_he: Mapped[str] = mapped_column(String(255), nullable=False)
    template_name_en: Mapped[str] = mapped_column(String(255), nullable=False)
    template_status: Mapped[TemplateStatus] = mapped_column(
        Enum(TemplateStatus, native_enum=False), default=TemplateStatus.DRAFT, nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.app_user_id"))

    field_definitions: Mapped[list["TemplateFieldDefinition"]] = relationship(
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="TemplateFieldDefinition.display_order",
    )


class Artifact(Base):
    __tablename__ = "artifact"

    artifact_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    artifact_type: Mapped[ArtifactType] = mapped_column(Enum(ArtifactType, native_enum=False), nullable=False)
    storage_uri: Mapped[str] = mapped_column(Text, nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)
    checksum: Mapped[str] = mapped_column(String(128), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.app_user_id"))
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TemplateFieldDefinition(Base):
    __tablename__ = "template_field_definition"
    __table_args__ = (UniqueConstraint("template_id", "field_key", name="uq_template_field_key"),)

    template_field_definition_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    template_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("template.template_id"), nullable=False)
    field_key: Mapped[str] = mapped_column(String(128), nullable=False)
    field_label_he: Mapped[str] = mapped_column(String(255), nullable=False)
    field_label_en: Mapped[str] = mapped_column(String(255), nullable=False)
    field_type: Mapped[FieldType] = mapped_column(Enum(FieldType, native_enum=False), nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_conditionally_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    submitter_editable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    reviewer_editable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    admin_editable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    lock_on_done: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    lock_on_closed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    validation_rule_ref: Mapped[str | None] = mapped_column(Text)

    template: Mapped[Template] = relationship(back_populates="field_definitions")


class TemplateSchemaSnapshot(Base):
    __tablename__ = "template_schema_snapshot"

    template_schema_snapshot_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    template_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("template.template_id"), nullable=False)
    template_version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    schema_json: Mapped[dict] = mapped_column(JSON_VARIANT, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.app_user_id"))
    artifact_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("artifact.artifact_id"))


class Workspace(TimestampMixin, Base):
    __tablename__ = "workspace"

    workspace_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    access_group_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("access_group.access_group_id"), nullable=False)
    template_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("template.template_id"), nullable=False)
    workspace_title: Mapped[str] = mapped_column(String(255), nullable=False)
    business_date: Mapped[date | None] = mapped_column(Date)
    workspace_status: Mapped[WorkspaceStatus] = mapped_column(
        Enum(WorkspaceStatus, native_enum=False), default=WorkspaceStatus.DRAFT, nullable=False
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.app_user_id"))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.app_user_id"))


class WorkspaceParticipant(Base):
    __tablename__ = "workspace_participant"
    __table_args__ = (
        UniqueConstraint("workspace_id", "app_user_id", "participant_role", name="uq_workspace_participant_role"),
    )

    workspace_participant_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspace.workspace_id"), nullable=False)
    app_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.app_user_id"), nullable=False)
    participant_role: Mapped[ParticipantRole] = mapped_column(Enum(ParticipantRole, native_enum=False), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    assigned_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.app_user_id"))
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LineItem(TimestampMixin, Base):
    __tablename__ = "line_item"
    __table_args__ = (UniqueConstraint("workspace_id", "line_item_key", name="uq_workspace_line_item_key"),)

    line_item_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspace.workspace_id"), nullable=False)
    line_item_key: Mapped[str] = mapped_column(String(128), nullable=False)
    line_item_title: Mapped[str] = mapped_column(String(255), nullable=False)
    line_item_status: Mapped[LineItemStatus] = mapped_column(
        Enum(LineItemStatus, native_enum=False), default=LineItemStatus.OPEN, nullable=False
    )
    closed_reason: Mapped[str | None] = mapped_column(Text)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.app_user_id"))


class WorkspaceRevision(Base):
    __tablename__ = "workspace_revision"
    __table_args__ = (UniqueConstraint("workspace_id", "revision_number", name="uq_workspace_revision_number"),)

    workspace_revision_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspace.workspace_id"), nullable=False)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.app_user_id"))
    revision_reason: Mapped[RevisionReason] = mapped_column(Enum(RevisionReason, native_enum=False), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class CurrentPayload(Base):
    __tablename__ = "current_payload"
    __table_args__ = (
        Index(
            "current_payload_line_item_current",
            "workspace_id",
            "line_item_id",
            unique=True,
            postgresql_where=expression.text("is_current = true AND line_item_id IS NOT NULL"),
            sqlite_where=expression.text("is_current = 1 AND line_item_id IS NOT NULL"),
        ),
        Index(
            "current_payload_workspace_current",
            "workspace_id",
            unique=True,
            postgresql_where=expression.text("is_current = true AND line_item_id IS NULL"),
            sqlite_where=expression.text("is_current = 1 AND line_item_id IS NULL"),
        ),
    )

    current_payload_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspace.workspace_id"), nullable=False)
    line_item_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("line_item.line_item_id"))
    workspace_revision_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspace_revision.workspace_revision_id"), nullable=False
    )
    template_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("template.template_id"), nullable=False)
    payload_json: Mapped[dict | None] = mapped_column(JSON_VARIANT)
    payload_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    payload_artifact_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("artifact.artifact_id"))
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PayloadSnapshot(Base):
    __tablename__ = "payload_snapshot"

    payload_snapshot_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspace.workspace_id"), nullable=False)
    line_item_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("line_item.line_item_id"))
    workspace_revision_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspace_revision.workspace_revision_id"), nullable=False
    )
    artifact_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("artifact.artifact_id"), nullable=False)
    snapshot_type: Mapped[SnapshotType] = mapped_column(Enum(SnapshotType, native_enum=False), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.app_user_id"))


class ClarificationRequest(Base):
    __tablename__ = "clarification_request"

    clarification_request_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspace.workspace_id"), nullable=False)
    line_item_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("line_item.line_item_id"))
    requested_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.app_user_id"), nullable=False)
    status: Mapped[ClarificationStatus] = mapped_column(
        Enum(ClarificationStatus, native_enum=False), default=ClarificationStatus.OPEN, nullable=False
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Comment(Base):
    __tablename__ = "comment"

    comment_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspace.workspace_id"), nullable=False)
    line_item_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("line_item.line_item_id"))
    clarification_request_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("clarification_request.clarification_request_id")
    )
    author_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.app_user_id"), nullable=False)
    visibility_type: Mapped[CommentVisibilityType] = mapped_column(
        Enum(CommentVisibilityType, native_enum=False), nullable=False
    )
    comment_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Recommendation(Base):
    __tablename__ = "recommendation"
    __table_args__ = (
        Index(
            "recommendation_current",
            "line_item_id",
            unique=True,
            postgresql_where=expression.text("superseded_at IS NULL"),
            sqlite_where=expression.text("superseded_at IS NULL"),
        ),
    )

    recommendation_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    line_item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("line_item.line_item_id"), nullable=False)
    recommended_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.app_user_id"), nullable=False)
    recommended_action: Mapped[RecommendedAction] = mapped_column(
        Enum(RecommendedAction, native_enum=False), nullable=False
    )
    recommended_final_value_json: Mapped[dict | None] = mapped_column(JSON_VARIANT)
    reason_text: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class FinalValue(Base):
    __tablename__ = "final_value"
    __table_args__ = (
        Index(
            "final_value_current",
            "line_item_id",
            unique=True,
            postgresql_where=expression.text("is_current = true"),
            sqlite_where=expression.text("is_current = 1"),
        ),
    )

    final_value_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    line_item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("line_item.line_item_id"), nullable=False)
    source_workspace_revision_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("workspace_revision.workspace_revision_id")
    )
    original_submitted_current_payload_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("current_payload.current_payload_id")
    )
    final_value_json: Mapped[dict] = mapped_column(JSON_VARIANT, nullable=False)
    override_reason: Mapped[str | None] = mapped_column(Text)
    approved_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.app_user_id"), nullable=False)
    approved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    superseded_by_final_value_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("final_value.final_value_id"))


class WorkspaceStatusHistory(Base):
    __tablename__ = "workspace_status_history"

    workspace_status_history_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspace.workspace_id"), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(64))
    to_status: Mapped[str] = mapped_column(String(64), nullable=False)
    changed_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.app_user_id"), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    change_reason: Mapped[str | None] = mapped_column(Text)


class LineItemStatusHistory(Base):
    __tablename__ = "line_item_status_history"

    line_item_status_history_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    line_item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("line_item.line_item_id"), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(64))
    to_status: Mapped[str] = mapped_column(String(64), nullable=False)
    changed_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.app_user_id"), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    change_reason: Mapped[str | None] = mapped_column(Text)


class ValidationIssue(Base):
    __tablename__ = "validation_issue"

    validation_issue_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspace.workspace_id"), nullable=False)
    line_item_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("line_item.line_item_id"))
    workspace_revision_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("workspace_revision.workspace_revision_id")
    )
    severity: Mapped[ValidationSeverity] = mapped_column(
        Enum(ValidationSeverity, native_enum=False), nullable=False
    )
    rule_code: Mapped[str] = mapped_column(String(128), nullable=False)
    message_he: Mapped[str] = mapped_column(Text, nullable=False)
    message_en: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[ValidationStatus] = mapped_column(
        Enum(ValidationStatus, native_enum=False), default=ValidationStatus.OPEN, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.app_user_id"))


class ArtifactLink(Base):
    __tablename__ = "artifact_link"
    __table_args__ = (
        Index("artifact_link_unique", "artifact_id", "entity_type", "entity_id", "link_role", unique=True),
    )

    artifact_link_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    artifact_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("artifact.artifact_id"), nullable=False)
    entity_type: Mapped[ArtifactEntityType] = mapped_column(
        Enum(ArtifactEntityType, native_enum=False), nullable=False
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    link_role: Mapped[ArtifactLinkRole] = mapped_column(Enum(ArtifactLinkRole, native_enum=False), nullable=False)
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    linked_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.app_user_id"))


class OutputBatch(Base):
    __tablename__ = "output_batch"

    output_batch_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    scope_type: Mapped[OutputScopeType] = mapped_column(Enum(OutputScopeType, native_enum=False), nullable=False)
    scope_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    generated_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.app_user_id"), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    export_artifact_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("artifact.artifact_id"))
    included_item_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    excluded_open_item_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    excluded_closed_item_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class OutputBatchItem(Base):
    __tablename__ = "output_batch_item"
    __table_args__ = (UniqueConstraint("output_batch_id", "line_item_id", name="uq_output_batch_line_item"),)

    output_batch_item_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    output_batch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("output_batch.output_batch_id"), nullable=False)
    line_item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("line_item.line_item_id"), nullable=False)
    final_value_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("final_value.final_value_id"), nullable=False)


class ArchiveCatalogEntry(Base):
    __tablename__ = "archive_catalog_entry"
    __table_args__ = {"schema": ARCHIVE_SCHEMA} if ARCHIVE_SCHEMA else {}

    archive_catalog_entry_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    artifact_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    line_item_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    template_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    workspace_revision_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    business_date: Mapped[date | None] = mapped_column(Date)
    access_group_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    status_at_archive_time: Mapped[str | None] = mapped_column(String(64))
    artifact_type: Mapped[ArtifactType] = mapped_column(Enum(ArtifactType, native_enum=False), nullable=False)
    archived_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    retention_class: Mapped[str | None] = mapped_column(String(128))


class ArchiveRestoreRequest(Base):
    __tablename__ = "archive_restore_request"

    archive_restore_request_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    archive_catalog_entry_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    requested_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.app_user_id"), nullable=False)
    status: Mapped[RestoreStatus] = mapped_column(
        Enum(RestoreStatus, native_enum=False), default=RestoreStatus.REQUESTED, nullable=False
    )
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reason: Mapped[str | None] = mapped_column(Text)
    failure_reason: Mapped[str | None] = mapped_column(Text)


class AuditEvent(Base):
    __tablename__ = "audit_event"

    audit_event_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.app_user_id"))
    company_person_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("company_person.company_person_id"))
    event_payload_json: Mapped[dict | None] = mapped_column(JSON_VARIANT)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
