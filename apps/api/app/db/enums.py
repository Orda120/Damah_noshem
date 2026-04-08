from __future__ import annotations

from enum import StrEnum


class LanguageCode(StrEnum):
    HE = "he"
    EN = "en"


class AuthType(StrEnum):
    USERNAME_PASSWORD = "username_password"


class RoleCode(StrEnum):
    SUBMITTER = "submitter"
    REVIEWER = "reviewer"
    MANAGER = "manager"
    ADMIN = "admin"
    GROUP_ADMIN = "group_admin"


class ScopeType(StrEnum):
    GLOBAL = "global"
    GROUP = "group"
    WORKSPACE = "workspace"


class AccessCodeType(StrEnum):
    GROUP_CREATION = "group_creation"


class AttemptStatus(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"


class GroupStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"
    ARCHIVED = "archived"


class MembershipRole(StrEnum):
    MEMBER = "member"
    GROUP_ADMIN = "group_admin"


class MembershipStatus(StrEnum):
    ACTIVE = "active"
    REVOKED = "revoked"
    PENDING = "pending"


class AccessDecisionType(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    CONDITIONAL = "conditional"


class TemplateStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    RETIRED = "retired"


class FieldType(StrEnum):
    TEXT = "text"
    NUMBER = "number"
    DATE = "date"
    SELECT = "select"
    FILE = "file"


class WorkspaceStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    NEEDS_CLARIFICATION = "needs_clarification"
    CLOSED = "closed"


class ParticipantRole(StrEnum):
    SUBMITTER = "submitter"
    REVIEWER = "reviewer"
    ADMIN = "admin"
    VIEWER = "viewer"


class LineItemStatus(StrEnum):
    OPEN = "open"
    DONE = "done"
    CLOSED = "closed"
    ARCHIVED = "archived"


class RevisionReason(StrEnum):
    SUBMITTER_EDIT = "submitter_edit"
    ADMIN_EDIT = "admin_edit"
    REOPEN_EDIT = "reopen_edit"


class SnapshotType(StrEnum):
    MONTHLY_ARCHIVE = "monthly_archive"
    CHECKPOINT = "checkpoint"
    PRE_DELETE_ARCHIVE = "pre_delete_archive"


class ClarificationStatus(StrEnum):
    OPEN = "open"
    ANSWERED = "answered"
    CLOSED = "closed"


class CommentVisibilityType(StrEnum):
    SUBMITTER_VISIBLE = "submitter_visible"
    INTERNAL_ONLY = "internal_only"


class RecommendedAction(StrEnum):
    DONE = "done"
    CLOSED = "closed"


class ValidationSeverity(StrEnum):
    BLOCKING = "blocking"
    WARNING = "warning"
    INFORMATIONAL = "informational"


class ValidationStatus(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"


class ArtifactType(StrEnum):
    UPLOADED_EXCEL = "uploaded_excel"
    EXPORT_EXCEL = "export_excel"
    PAYLOAD_SNAPSHOT = "payload_snapshot"
    TEMPLATE_SNAPSHOT = "template_snapshot"
    OTHER = "other"


class ArtifactEntityType(StrEnum):
    WORKSPACE = "workspace"
    LINE_ITEM = "line_item"
    TEMPLATE_SNAPSHOT = "template_snapshot"
    PAYLOAD_SNAPSHOT = "payload_snapshot"


class ArtifactLinkRole(StrEnum):
    SOURCE_UPLOAD = "source_upload"
    ARCHIVE_SNAPSHOT = "archive_snapshot"
    ATTACHMENT = "attachment"


class OutputScopeType(StrEnum):
    BUSINESS_DATE = "business_date"
    GROUP = "group"
    CUSTOM = "custom"
