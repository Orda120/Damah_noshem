# Entity Relationship Design (ERD) Specification

## Product
Daily Submissions Review and Reconciliation Web App

## Status
Draft v5 — approved direction with archive-stub rule

## Purpose
Translate the PRD into a practical implementation-facing data model, with identity and access entities defined first, followed by workspace, review, output, and storage entities.

This ERD is split into two parts:

1. Identity and Access Model
2. Workspace, Review, Output, and Storage Model

That order is deliberate because workspace visibility, permissioning, and auditability depend on the access model.

---

## Database Platform

**PostgreSQL** (Azure Database for PostgreSQL Flexible Server)

- Relational model with foreign key enforcement throughout
- Row-level security supports compartmentalization at the database layer
- Partial indexes enforce `is_current = true` uniqueness on `FinalValue` and `CurrentPayload`
- JSONB for payload storage; no platform change required if dynamic templates are needed later
- Append-only audit tables are safe and performant

---

## Storage Architecture

The system uses a three-layer hybrid storage model:

| Layer | What lives here | Technology |
|---|---|---|
| Hot operational DB | Current state, schema versions, recent revisions, current payload JSON, audit events, active metadata | PostgreSQL |
| Artifact storage | Excel uploads, generated exports, archived JSON snapshots, template snapshots, large/cold files | Azure Blob Storage |
| Archive catalog DB | Searchable metadata and file pointers for archived artifacts; no full payloads | PostgreSQL (separate schema or DB) |

**Key rules:**
- Excel files are artifacts, not the primary source of truth
- Current and recent payload JSON stays in the hot DB for fast access
- Older payload revisions are snapshotted to artifact storage on a defined retention schedule
- The archive catalog stores only metadata and pointers, never full payload content
- Rows referenced by append-only history entities are never physically deleted from the hot DB; only heavy content fields may be archived and nulled

---

## 1. Modeling Principles

- Every user-facing permission decision must be enforceable server-side
- Every active user must map to a single internal company person identity
- Authentication method and application identity are not the same thing
- Group-based access is core to compartmentalization
- Reviewer recommendation is separate from admin lifecycle action
- Done and Closed are business outcomes; Archived is a visibility/archive state
- Field-level editability is driven by role + state + template policy
- Payload JSON is the operational field-value storage format for MVP
- FinalValue stores its value as JSON consistent with the payload model
- Audit records must be append-only
- Global admin bypasses group membership and workspace participation checks; all other roles do not
- Rows referenced by append-only history entities are never deleted; only heavy content fields are archived/nulled

---

## 2. ERD Part 1: Identity and Access

### 2.1 Entity: CompanyPerson

**Purpose**  
Canonical internal person identity from the organization. The anchor for authorization and audit.

**Key Fields**
- `company_person_id` (PK)
- `employee_number`
- `full_name_he`
- `full_name_en`
- `email`
- `department`
- `is_active`
- `created_at`
- `updated_at`

**Notes**
- A person may authenticate through more than one method, but all methods must resolve to the same CompanyPerson via AppUser.
- AuthIdentity links to AppUser, not directly to CompanyPerson.

**Relationships**
- one CompanyPerson to one AppUser
- one CompanyPerson to many audit actions (via AppUser)

---

### 2.2 Entity: AppUser

**Purpose**  
Application-level user account for authorization, preferences, and account state.

**Key Fields**
- `app_user_id` (PK)
- `company_person_id` (FK -> CompanyPerson)
- `default_language` (`he`, `en`)
- `is_enabled`
- `is_locked`
- `last_login_at`
- `created_at`
- `updated_at`

**Notes**
- Kept separate from CompanyPerson to support application-specific settings and lock state without mutating the source corporate identity.
- One CompanyPerson maps to exactly one AppUser.

**Relationships**
- one AppUser to one CompanyPerson
- one AppUser to many AuthIdentity
- one AppUser to many UserRoleAssignment
- one AppUser to many WorkspaceParticipant
- one AppUser to many GroupMembership
- one AppUser to many authored records

---

### 2.3 Entity: AuthIdentity

**Purpose**  
Represents a sign-in method linked to an AppUser.

**Key Fields**
- `auth_identity_id` (PK)
- `app_user_id` (FK -> AppUser)
- `auth_type` (`sso`, `username_password`)
- `external_subject` (nullable)
- `username` (nullable)
- `password_hash` (nullable)
- `is_primary`
- `is_verified`
- `linked_at`
- `last_used_at`
- `created_at`
- `disabled_at` (nullable)

**Notes**
- Prevents duplicate person records by forcing all login methods to resolve to the same AppUser.
- Recommended identity-linking rule: if a CompanyPerson match already exists, block automatic second-user creation and route to supervised linking.

**Relationships**
- many AuthIdentity to one AppUser

---

### 2.4 Entity: Role

**Purpose**  
Defines the set of application roles.

**Key Fields**
- `role_id` (PK)
- `role_code` (`submitter`, `reviewer`, `manager`, `admin`, `group_admin`)
- `display_name_he`
- `display_name_en`
- `is_system_role`

**Notes**
- MVP role set is intentionally small.
- `admin` is the global admin role.

**Relationships**
- one Role to many UserRoleAssignment

---

### 2.5 Entity: UserRoleAssignment

**Purpose**  
Assigns one or more roles to a user, optionally scoped to a group or workspace.

**Key Fields**
- `user_role_assignment_id` (PK)
- `app_user_id` (FK -> AppUser)
- `role_id` (FK -> Role)
- `scope_type` (`global`, `group`, `workspace`)
- `scope_id` (nullable)
- `granted_by_user_id` (FK -> AppUser)
- `granted_at`
- `revoked_at` (nullable)
- `revoked_by_user_id` (nullable FK -> AppUser)

**Notes**
- MVP uses global scope for submitter, reviewer, manager, and admin.
- `group_admin` uses group scope.
- Every grant and revocation produces an AuditEvent.

**Relationships**
- many UserRoleAssignment to one AppUser
- many UserRoleAssignment to one Role

---

### 2.6 Entity: AccessCode

**Purpose**  
Controls restricted group creation by requiring a valid access code.

**Key Fields**
- `access_code_id` (PK)
- `code_value_hash`
- `code_type` (`group_creation`)
- `issued_by_user_id` (FK -> AppUser)
- `issued_for_scope` (nullable)
- `max_uses`
- `use_count`
- `expires_at`
- `is_revoked`
- `created_at`
- `revoked_at` (nullable)

**Relationships**
- one AccessCode to many GroupCreationEvent

---

### 2.7 Entity: GroupCreationEvent

**Purpose**  
Records every successful or failed access-code-based group creation attempt.

**Key Fields**
- `group_creation_event_id` (PK)
- `access_code_id` (FK -> AccessCode)
- `created_group_id` (nullable FK -> AccessGroup)
- `created_by_user_id` (FK -> AppUser)
- `attempt_status` (`success`, `failed`)
- `failure_reason` (nullable)
- `created_at`

**Notes**
- AccessGroup does not hold a back-reference FK to GroupCreationEvent. This avoids circular dependency.

**Relationships**
- many GroupCreationEvent to one AccessCode
- many GroupCreationEvent to one AppUser
- zero or one GroupCreationEvent to one AccessGroup

---

### 2.8 Entity: AccessGroup

**Purpose**  
Compartmentalized group. Primary boundary for access control and workspace scoping.

**Key Fields**
- `access_group_id` (PK)
- `group_name`
- `group_description`
- `created_by_user_id` (FK -> AppUser)
- `group_status` (`active`, `disabled`, `archived`)
- `created_at`
- `updated_at`

**Notes**
- Every workspace belongs to exactly one AccessGroup in MVP.

**Relationships**
- one AccessGroup to many GroupMembership
- one AccessGroup to many Workspace

---

### 2.9 Entity: GroupMembership

**Purpose**  
User membership in an AccessGroup, including role within that group.

**Key Fields**
- `group_membership_id` (PK)
- `access_group_id` (FK -> AccessGroup)
- `app_user_id` (FK -> AppUser)
- `membership_role` (`member`, `group_admin`)
- `membership_status` (`active`, `revoked`, `pending`)
- `granted_by_user_id` (FK -> AppUser)
- `granted_at`
- `revoked_by_user_id` (nullable FK -> AppUser)
- `revoked_at` (nullable)
- `revocation_reason` (nullable)

**Notes**
- Primary source for group-level access decisions for non-admin users.
- Global admin users bypass this check.
- If a group admin is revoked: future grants by that user are blocked immediately. Existing records remain until explicitly revoked.
- Every grant and revocation must produce an AuditEvent.

**Relationships**
- many GroupMembership to one AccessGroup
- many GroupMembership to one AppUser

---

### 2.10 Entity: AccessPolicyDecision

**Purpose**  
Cached decisions from the optional internal allowlist / firewall-style integration.

**Key Fields**
- `access_policy_decision_id` (PK)
- `app_user_id` (nullable FK -> AppUser)
- `company_person_id` (nullable FK -> CompanyPerson)
- `source_system`
- `decision_type` (`allow`, `deny`, `conditional`)
- `decision_reason` (nullable)
- `decision_payload_ref` (nullable)
- `evaluated_at`
- `expires_at` (nullable)

**Notes**
- When integration is disabled this table is unused but schema-present.
- Global admin is not exempt from this check when integration is enabled.

**Relationships**
- many AccessPolicyDecision to one AppUser
- many AccessPolicyDecision to one CompanyPerson

---

## 3. Identity and Access Relationship Summary

**Core chain**  
CompanyPerson → AppUser → AuthIdentity

**Group chain**  
AccessGroup → GroupMembership → AppUser

**Permission chain**  
AppUser → UserRoleAssignment  
AccessGroup → GroupMembership → AppUser  
Workspace → WorkspaceParticipant → AppUser

**Controlled creation chain**  
AccessCode → GroupCreationEvent → AccessGroup

**MVP authorization resolution order**

| Step | Check | Applies to |
|---|---|---|
| 1 | AppUser.is_enabled = true AND is_locked = false | All roles |
| 2 | UserRoleAssignment grants the required role | All roles |
| 3 | GroupMembership.membership_status = active for the relevant AccessGroup | All roles except global admin |
| 4 | WorkspaceParticipant exists with required participant_role for the workspace | All roles except global admin |
| 5 | If AccessPolicyDecision integration is enabled: latest non-expired decision is `allow` | All roles including global admin |

**Global admin bypass rule:**
A user with `role_code = admin` and `scope_type = global` passes steps 3 and 4 automatically. This bypass must be explicit in authorization middleware and logged in AuditEvent with `event_type = admin_bypass_applied`.

---

## 4. ERD Part 2: Workspace, Review, Output, and Storage

### 4.1 Entity: Template

**Purpose**  
Defines the structure, field configuration, and rules for a workspace type.

**Key Fields**
- `template_id` (PK)
- `template_code`
- `template_name_he`
- `template_name_en`
- `template_status` (`draft`, `active`, `retired`)
- `version_number`
- `created_by_user_id` (FK -> AppUser)
- `created_at`
- `updated_at`

**Relationships**
- one Template to many TemplateFieldDefinition
- one Template to many Workspace
- one Template to many TemplateSchemaSnapshot

---

### 4.2 Entity: TemplateFieldDefinition

**Purpose**  
Configuration model for template fields, editability policy, and validation hooks.

**Key Fields**
- `template_field_definition_id` (PK)
- `template_id` (FK -> Template)
- `field_key`
- `field_label_he`
- `field_label_en`
- `field_type` (`text`, `number`, `date`, `select`, `file`)
- `is_required`
- `is_conditionally_required`
- `submitter_editable`
- `reviewer_editable`
- `admin_editable`
- `lock_on_done`
- `lock_on_closed`
- `display_order`
- `validation_rule_ref` (nullable)

**Notes**
- Defines the schema that `payload_json` must conform to for each template.

**Relationships**
- many TemplateFieldDefinition to one Template

---

### 4.3 Entity: TemplateSchemaSnapshot

**Purpose**  
Immutable snapshot of a template schema version for replay and archive.

**Key Fields**
- `template_schema_snapshot_id` (PK)
- `template_id` (FK -> Template)
- `template_version_number`
- `schema_json`
- `created_at`
- `created_by_user_id` (FK -> AppUser)
- `artifact_id` (nullable FK -> Artifact)

**Notes**
- Write a snapshot whenever a template is retired or changed in a backward-incompatible way.

**Relationships**
- many TemplateSchemaSnapshot to one Template
- many TemplateSchemaSnapshot to one Artifact

---

### 4.4 Entity: Workspace

**Purpose**  
Admin-opened case or workspace for a person or group.

**Key Fields**
- `workspace_id` (PK)
- `access_group_id` (FK -> AccessGroup)
- `template_id` (FK -> Template)
- `workspace_title`
- `business_date` (nullable)
- `workspace_status` (`draft`, `active`, `needs_clarification`, `closed`)
- `created_by_user_id` (FK -> AppUser)
- `created_at`
- `updated_at`
- `closed_at` (nullable)
- `closed_by_user_id` (nullable FK -> AppUser)

**Notes**
- Every workspace belongs to exactly one AccessGroup.
- Submitter identity is determined by WorkspaceParticipant with `participant_role = submitter`.

**Relationships**
- one Workspace to many WorkspaceParticipant
- one Workspace to many LineItem
- one Workspace to many WorkspaceRevision
- one Workspace to many Comment
- one Workspace to many WorkspaceStatusHistory
- one Workspace to many ValidationIssue
- one Workspace to many ArtifactLink
- one Workspace to many ArchiveCatalogEntry (soft refs)

---

### 4.5 Entity: WorkspaceParticipant

**Purpose**  
Associates a user to a workspace with an explicit role.

**Key Fields**
- `workspace_participant_id` (PK)
- `workspace_id` (FK -> Workspace)
- `app_user_id` (FK -> AppUser)
- `participant_role` (`submitter`, `reviewer`, `admin`, `viewer`)
- `assigned_at`
- `assigned_by_user_id` (FK -> AppUser)
- `removed_at` (nullable)

**Notes**
- Global admin users do not require a WorkspaceParticipant record to access a workspace.

**Relationships**
- many WorkspaceParticipant to one Workspace
- many WorkspaceParticipant to one AppUser

---

### 4.6 Entity: LineItem

**Purpose**  
One discussion or reconciliation item within a workspace.

**Key Fields**
- `line_item_id` (PK)
- `workspace_id` (FK -> Workspace)
- `line_item_key`
- `line_item_title`
- `line_item_status` (`open`, `done`, `closed`, `archived`)
- `closed_reason` (nullable)
- `created_at`
- `created_by_user_id` (FK -> AppUser)
- `updated_at`

**Notes**
- No `current_revision_id` field. Latest effective values are derived from CurrentPayload where `is_current = true`.
- Workspace and line-item statuses are independent.

**Relationships**
- many LineItem to one Workspace
- one LineItem to many ClarificationRequest
- one LineItem to many Recommendation
- one LineItem to many LineItemStatusHistory
- one LineItem to many FinalValue
- one LineItem to many CurrentPayload
- one LineItem to many ValidationIssue
- one LineItem to many ArtifactLink
- one LineItem to many ArchiveCatalogEntry (soft refs)

---

### 4.7 Entity: WorkspaceRevision

**Purpose**  
Tracked revision of workspace data.

**Key Fields**
- `workspace_revision_id` (PK)
- `workspace_id` (FK -> Workspace)
- `revision_number`
- `created_by_user_id` (FK -> AppUser)
- `revision_reason` (`submitter_edit`, `admin_edit`, `reopen_edit`)
- `created_at`

**Notes**
- Created only when field values change, not on comment-only activity.
- Revisions stay in the hot DB inside the retention window.
- Older revisions are snapshotted to artifact storage.
- Revision rows themselves are not physically deleted if referenced by append-only history.

**Relationships**
- many WorkspaceRevision to one Workspace
- one WorkspaceRevision to many CurrentPayload
- one WorkspaceRevision to many PayloadSnapshot
- one WorkspaceRevision to many ValidationIssue
- one WorkspaceRevision to many FinalValue

---

### 4.8 Entity: CurrentPayload

**Purpose**  
Current or recent payload JSON for a workspace or line item at a specific revision.

**Key Fields**
- `current_payload_id` (PK)
- `workspace_id` (FK -> Workspace)
- `line_item_id` (nullable FK -> LineItem)
- `workspace_revision_id` (FK -> WorkspaceRevision)
- `template_id` (FK -> Template)
- `payload_json` (JSONB, nullable after archival)
- `payload_archived` (boolean, default false)
- `payload_artifact_id` (nullable FK -> Artifact)
- `is_current`
- `created_at`
- `archived_at` (nullable)

**Notes**
- Stored in the hot operational DB.
- `payload_json` must conform to TemplateFieldDefinition for the associated template.
- When archived, the row remains in the hot DB as a stub. Only the heavy `payload_json` content is moved to artifact storage and then nulled.
- `payload_artifact_id` points directly to the archived payload artifact.
- This preserves hard references from append-only history entities such as FinalValue.
- `line_item_id` is nullable because some templates may store workspace-level payload rather than line-item payload.

**Indexes**
For line-item-scoped payload rows:
```sql
CREATE UNIQUE INDEX current_payload_line_item_current
  ON current_payload (workspace_id, line_item_id)
  WHERE is_current = true AND line_item_id IS NOT NULL;
```

For workspace-level payload rows:
```sql
CREATE UNIQUE INDEX current_payload_workspace_current
  ON current_payload (workspace_id)
  WHERE is_current = true AND line_item_id IS NULL;
```

**Relationships**
- many CurrentPayload to one Workspace
- many CurrentPayload to one LineItem (when line-item-scoped)
- many CurrentPayload to one WorkspaceRevision
- many CurrentPayload to one Artifact (when archived)

---

### 4.9 Entity: PayloadSnapshot

**Purpose**  
Archive record for a payload revision flushed from the hot DB to artifact storage.

**Key Fields**
- `payload_snapshot_id` (PK)
- `workspace_id` (FK -> Workspace)
- `line_item_id` (nullable FK -> LineItem)
- `workspace_revision_id` (FK -> WorkspaceRevision)
- `artifact_id` (FK -> Artifact)
- `snapshot_type` (`monthly_archive`, `checkpoint`, `pre_delete_archive`)
- `created_at`
- `created_by_user_id` (FK -> AppUser)

**Notes**
- The file lives in artifact storage. This entity keeps the link and metadata.
- Used when old payload revisions are archived from hot storage.

**Relationships**
- many PayloadSnapshot to one Workspace
- many PayloadSnapshot to one LineItem
- many PayloadSnapshot to one WorkspaceRevision
- many PayloadSnapshot to one Artifact

---

### 4.10 Entity: ClarificationRequest

**Purpose**  
One clarification cycle initiated by a reviewer or admin.

**Key Fields**
- `clarification_request_id` (PK)
- `workspace_id` (FK -> Workspace)
- `line_item_id` (nullable FK -> LineItem)
- `requested_by_user_id` (FK -> AppUser)
- `status` (`open`, `answered`, `closed`)
- `message`
- `created_at`
- `answered_at` (nullable)
- `closed_at` (nullable)

**Notes**
- One ClarificationRequest represents one clarification cycle in MVP.
- Status transitions: `open -> answered -> closed`.

**Relationships**
- many ClarificationRequest to one Workspace
- many ClarificationRequest to one LineItem
- one ClarificationRequest to many Comment

---

### 4.11 Entity: Comment

**Purpose**  
All communication and notes on a workspace or line item.

**Key Fields**
- `comment_id` (PK)
- `workspace_id` (FK -> Workspace)
- `line_item_id` (nullable FK -> LineItem)
- `clarification_request_id` (nullable FK -> ClarificationRequest)
- `author_user_id` (FK -> AppUser)
- `visibility_type` (`submitter_visible`, `internal_only`)
- `comment_text`
- `created_at`

**Notes**
- `visibility_type` is set explicitly at creation and never changed.
- `internal_only` comments must be excluded at query level from submitter-facing responses.

**Relationships**
- many Comment to one Workspace
- many Comment to one LineItem
- many Comment to one ClarificationRequest

---

### 4.12 Entity: Recommendation

**Purpose**  
Reviewer recommendation for the lifecycle outcome of a line item.

**Key Fields**
- `recommendation_id` (PK)
- `line_item_id` (FK -> LineItem)
- `recommended_by_user_id` (FK -> AppUser)
- `recommended_action` (`done`, `closed`)
- `recommended_final_value_json` (nullable)
- `reason_text` (nullable)
- `created_at`
- `superseded_at` (nullable)

**Notes**
- Advisory only; does not change line-item status.
- Only one active recommendation per line item in MVP.

**Relationships**
- many Recommendation to one LineItem
- many Recommendation to one AppUser

---

### 4.13 Entity: FinalValue

**Purpose**  
Append-only official value decision history for a line item.

**Key Fields**
- `final_value_id` (PK)
- `line_item_id` (FK -> LineItem)
- `source_workspace_revision_id` (nullable FK -> WorkspaceRevision)
- `original_submitted_current_payload_id` (nullable FK -> CurrentPayload)
- `final_value_json`
- `override_reason` (nullable)
- `approved_by_user_id` (FK -> AppUser)
- `approved_at`
- `is_current` (boolean)
- `superseded_at` (nullable)
- `superseded_by_final_value_id` (nullable FK -> FinalValue)

**Notes**
- Append-only. Rows are never deleted.
- A new Done action supersedes the previous current row.
- `original_submitted_current_payload_id` is a hard FK to CurrentPayload. This is safe because CurrentPayload rows are never physically deleted; only payload_json may be archived/nulled.
- Retrieval path after archival is direct: `FinalValue -> CurrentPayload -> Artifact` through `payload_artifact_id`.

**Index**
```sql
CREATE UNIQUE INDEX final_value_current
  ON final_value (line_item_id)
  WHERE is_current = true;
```

**Relationships**
- many FinalValue to one LineItem
- many FinalValue to one AppUser
- many FinalValue to one WorkspaceRevision
- many FinalValue to one CurrentPayload

---

### 4.14 Entity: WorkspaceStatusHistory

**Purpose**  
Append-only log of every workspace status transition.

**Key Fields**
- `workspace_status_history_id` (PK)
- `workspace_id` (FK -> Workspace)
- `from_status`
- `to_status`
- `changed_by_user_id` (FK -> AppUser)
- `changed_at`
- `change_reason` (nullable)

---

### 4.15 Entity: LineItemStatusHistory

**Purpose**  
Append-only log of every line item lifecycle transition.

**Key Fields**
- `line_item_status_history_id` (PK)
- `line_item_id` (FK -> LineItem)
- `from_status`
- `to_status`
- `changed_by_user_id` (FK -> AppUser)
- `changed_at`
- `change_reason` (nullable)

---

### 4.16 Entity: ValidationIssue

**Purpose**  
Validation result for a workspace or line item at a specific revision.

**Key Fields**
- `validation_issue_id` (PK)
- `workspace_id` (FK -> Workspace)
- `line_item_id` (nullable FK -> LineItem)
- `workspace_revision_id` (nullable FK -> WorkspaceRevision)
- `severity` (`blocking`, `warning`, `informational`)
- `rule_code`
- `message_he`
- `message_en`
- `status` (`open`, `resolved`)
- `created_at`
- `resolved_at` (nullable)
- `resolved_by_user_id` (nullable FK -> AppUser)

**Notes**
- `ignored` is not valid in MVP.
- A Done action is blocked while any blocking open ValidationIssue exists for the relevant item.

**Relationships**
- many ValidationIssue to one Workspace
- many ValidationIssue to one LineItem
- many ValidationIssue to one WorkspaceRevision

---

### 4.17 Entity: Artifact

**Purpose**  
Canonical file and artifact registry.

**Key Fields**
- `artifact_id` (PK)
- `artifact_type` (`uploaded_excel`, `export_excel`, `payload_snapshot`, `template_snapshot`, `other`)
- `storage_uri`
- `file_name`
- `mime_type`
- `checksum`
- `file_size_bytes`
- `created_at`
- `created_by_user_id` (FK -> AppUser)
- `archived_at` (nullable)

**Notes**
- Single registry for all file artifacts.

**Relationships**
- one Artifact to many ArtifactLink
- one Artifact to many ArchiveCatalogEntry
- one Artifact to many PayloadSnapshot
- one Artifact to many TemplateSchemaSnapshot
- one Artifact to many CurrentPayload (archived payload references)

---

### 4.18 Entity: ArtifactLink

**Purpose**  
Polymorphic link between an artifact and a business entity.

**Key Fields**
- `artifact_link_id` (PK)
- `artifact_id` (FK -> Artifact)
- `entity_type` (`workspace`, `line_item`, `template_snapshot`, `payload_snapshot`)
- `entity_id`
- `link_role` (`source_upload`, `archive_snapshot`, `attachment`)
- `linked_at`
- `linked_by_user_id` (FK -> AppUser)

**Notes**
- OutputBatch uses direct FK to Artifact, not ArtifactLink.

**Uniqueness**
```sql
CREATE UNIQUE INDEX artifact_link_unique
  ON artifact_link (artifact_id, entity_type, entity_id, link_role);
```

**Relationships**
- many ArtifactLink to one Artifact

---

### 4.19 Entity: OutputBatch

**Purpose**  
Single final output or export generation event for a given scope.

**Key Fields**
- `output_batch_id` (PK)
- `scope_type` (`business_date`, `group`, `custom`)
- `scope_ref`
- `generated_by_user_id` (FK -> AppUser)
- `generated_at`
- `export_artifact_id` (nullable FK -> Artifact)
- `included_item_count`
- `excluded_open_item_count`
- `excluded_closed_item_count`

**Notes**
- Direct FK to Artifact is sufficient and unambiguous.

**Relationships**
- one OutputBatch to many OutputBatchItem
- one OutputBatch to one Artifact

---

### 4.20 Entity: OutputBatchItem

**Purpose**  
Links each Done line item included in an output batch to its final value at generation time.

**Key Fields**
- `output_batch_item_id` (PK)
- `output_batch_id` (FK -> OutputBatch)
- `line_item_id` (FK -> LineItem)
- `final_value_id` (FK -> FinalValue)

**Notes**
- Only Done line items appear here.
- `final_value_id` must reference the current FinalValue at generation time.

---

### 4.21 Entity: ArchiveCatalogEntry

**Purpose**  
Searchable metadata and file pointer for an archived artifact. Lives in the archive catalog DB. Never stores full payload content.

**Key Fields**
- `archive_catalog_entry_id` (PK)
- `artifact_id` (soft reference to Artifact.artifact_id)
- `workspace_id` (soft reference)
- `line_item_id` (soft reference)
- `template_id` (soft reference)
- `workspace_revision_id` (soft reference)
- `business_date` (nullable)
- `access_group_id` (soft reference)
- `status_at_archive_time` (nullable)
- `artifact_type`
- `archived_at`
- `retention_class` (nullable)

**Notes**
- Lives in a separate archive catalog DB, so these are soft references, not enforced cross-DB foreign keys.
- Metadata-only. No payload content is duplicated here.

---

### 4.22 Entity: AuditEvent

**Purpose**  
Cross-cutting append-only log for security and system events not captured by domain status history tables.

**Key Fields**
- `audit_event_id` (PK)
- `event_type`
- `entity_type`
- `entity_id`
- `actor_user_id` (nullable FK -> AppUser)
- `company_person_id` (nullable FK -> CompanyPerson)
- `event_payload_json`
- `created_at`

**Notes**
- Records are never updated or deleted.
- `event_payload_json` should capture before/after state for mutation events.
- Global admin bypass events must be logged with `event_type = admin_bypass_applied`.

---

## 5. Relationship Summary

**Template chain**  
Template → TemplateFieldDefinition  
Template → TemplateSchemaSnapshot → Artifact

**Workspace chain**  
AccessGroup → Workspace → LineItem  
Workspace → WorkspaceParticipant → AppUser

**Revision and payload chain**  
Workspace → WorkspaceRevision → CurrentPayload  
WorkspaceRevision → PayloadSnapshot → Artifact  
FinalValue → CurrentPayload → Artifact (when archived)

**Review chain**  
Workspace / LineItem → ClarificationRequest → Comment  
LineItem → Recommendation  
LineItem → FinalValue  
Workspace / LineItem / WorkspaceRevision → ValidationIssue

**History chain**  
Workspace → WorkspaceStatusHistory  
LineItem → LineItemStatusHistory

**Artifact chain**  
Artifact → ArtifactLink  
Artifact → ArchiveCatalogEntry (soft references)

**Output chain**  
OutputBatch → OutputBatchItem → LineItem → FinalValue  
OutputBatch → Artifact

---

## 6. Blocking Decisions Before Physical Schema

1. **Identity linking rule**  
How SSO and username/password resolve to one AppUser and one CompanyPerson

2. **Template finalization**  
Which MVP templates exist and what fields each requires

3. **Hot DB retention window**  
How long WorkspaceRevision and CurrentPayload rows stay in the hot DB before archival

4. **Archive restore rule**  
How archived payloads and artifacts are rehydrated for authorized users

5. **Workspace group-scoping rule**  
Whether every workspace must belong to exactly one AccessGroup in MVP

6. **Group admin revocation behavior**  
What happens to assignments and memberships previously created by a revoked group admin

7. **Template snapshot trigger rule**  
Exactly when a TemplateSchemaSnapshot must be written

---

## 7. Recommended MVP Simplifications

1. Keep Role set small: submitter, reviewer, manager, admin, group_admin only
2. Use GroupMembership + WorkspaceParticipant + UserRoleAssignment for all access decisions
3. Use one AccessCode type for group creation only
4. Keep TemplateFieldDefinition as a configuration model; do not build a dynamic form builder
5. Store current and recent payload JSON in the hot DB; archive older revisions on a monthly schedule
6. Allow only one active non-superseded recommendation per line item
7. Make OutputBatch generation synchronous for MVP
8. Keep ArchiveCatalogEntry metadata-only; never duplicate payload content there
9. Enforce all `is_current` and ArtifactLink uniqueness constraints at the database level

---

## 8. Decision Log

| Decision | Change Applied |
|---|---|
| Remove LineItem.current_revision_id | Removed. Latest values derived by querying CurrentPayload with is_current = true. |
| FinalValue append-only with supersession | Applied. is_current, superseded_at, superseded_by_final_value_id in place. |
| Remove AccessGrant from MVP | Removed from all entities and relationship summaries. |
| Remove Workspace.owner_user_id | Removed. Submitter identity comes from WorkspaceParticipant. |
| Tighten ClarificationRequest lifecycle | Applied. Statuses: open, answered, closed. |
| Remove ValidationIssue.status = ignored | Removed. MVP statuses: open, resolved only. |
| FinalValue storage type resolved | final_value_json adopted. Consistent with CurrentPayload and Recommendation. |
| Duplicate AccessPolicyDecision section | Removed. One section only. |
| Stale AccessGrant references | Removed from relationship lists. |
| CompanyPerson → AuthIdentity direct relationship | Corrected. Chain is CompanyPerson → AppUser → AuthIdentity. |
| OutputBatch dual path to Artifact | Resolved. Direct FK via export_artifact_id only. |
| Partial indexes for is_current | Documented explicitly for FinalValue and CurrentPayload. |
| Hybrid storage model | Adopted. Three-layer model documented. |
| Circular FK between AccessGroup and GroupCreationEvent | Resolved. GroupCreationEvent.created_group_id is the only forward reference. |
| Admin bypass in authorization resolution order | Resolved. Global admin bypasses steps 3 and 4 only. |
| CurrentPayload null line_item_id uniqueness gap | Resolved. Separate partial indexes for line-item and workspace-level payloads. |
| original_submitted_payload_ref underdefined | Resolved as original_submitted_current_payload_id FK -> CurrentPayload. |
| ArtifactLink uniqueness constraint | Resolved with unique index on (artifact_id, entity_type, entity_id, link_role). |
| Archive deletion vs hard FK inconsistency | Resolved. CurrentPayload rows referenced by append-only history are kept as stub rows; only payload_json is archived/nulled. |
| Direct retrieval path for archived original payload | Resolved. FinalValue -> CurrentPayload -> Artifact path documented. |

---

*Document maintained by: [Product Owner name]*  
*Last updated: [date]*  
*Status: Draft v5 — ready for API design after blocking decisions in section 6 are resolved*
