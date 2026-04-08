from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select

from app.core.security import hash_password
from app.db.base import Base
from app.db.enums import (
    AccessCodeType,
    ArtifactType,
    AuthType,
    ClarificationStatus,
    CommentVisibilityType,
    FieldType,
    LanguageCode,
    LineItemStatus,
    MembershipRole,
    MembershipStatus,
    ParticipantRole,
    RecommendedAction,
    RevisionReason,
    RoleCode,
    ScopeType,
    TemplateStatus,
    ValidationSeverity,
    ValidationStatus,
    WorkspaceStatus,
)
from app.db.models import (
    AccessCode,
    AccessGroup,
    AppUser,
    Artifact,
    AuthIdentity,
    ClarificationRequest,
    Comment,
    CompanyPerson,
    CurrentPayload,
    FinalValue,
    GroupMembership,
    LineItem,
    LineItemStatusHistory,
    Recommendation,
    Role,
    Template,
    TemplateFieldDefinition,
    UserRoleAssignment,
    ValidationIssue,
    Workspace,
    WorkspaceParticipant,
    WorkspaceRevision,
    WorkspaceStatusHistory,
)
from app.db.session import SessionLocal, engine
from app.services.workflow import hash_access_code


def ensure_roles(session) -> dict[RoleCode, Role]:
    existing = {
        role.role_code: role
        for role in session.scalars(select(Role)).all()
    }
    labels = {
        RoleCode.SUBMITTER: ("מגיש", "Submitter"),
        RoleCode.REVIEWER: ("בודק", "Reviewer"),
        RoleCode.MANAGER: ("מנהל", "Manager"),
        RoleCode.ADMIN: ("אדמין", "Admin"),
        RoleCode.GROUP_ADMIN: ("מנהל קבוצה", "Group Admin"),
    }
    for role_code, (he, en) in labels.items():
        if role_code not in existing:
            role = Role(role_code=role_code, display_name_he=he, display_name_en=en, is_system_role=True)
            session.add(role)
            session.flush()
            existing[role_code] = role
    return existing


def ensure_user(
    session,
    *,
    employee_number: str,
    full_name_he: str,
    full_name_en: str,
    email: str,
    username: str,
    password: str,
    language: LanguageCode,
) -> AppUser:
    user = session.scalar(select(AppUser).join(CompanyPerson).where(CompanyPerson.employee_number == employee_number))
    if user:
        return user
    person = CompanyPerson(
        employee_number=employee_number,
        full_name_he=full_name_he,
        full_name_en=full_name_en,
        email=email,
        department="Operations",
        is_active=True,
    )
    session.add(person)
    session.flush()
    user = AppUser(company_person_id=person.company_person_id, default_language=language, is_enabled=True, is_locked=False)
    session.add(user)
    session.flush()
    session.add(
        AuthIdentity(
            app_user_id=user.app_user_id,
            auth_type=AuthType.USERNAME_PASSWORD,
            username=username,
            password_hash=hash_password(password),
            is_primary=True,
            is_verified=True,
        )
    )
    return user


def ensure_role_assignment(session, *, user: AppUser, role: Role, scope_type: ScopeType, scope_id=None) -> None:
    exists = session.scalar(
        select(UserRoleAssignment).where(
            UserRoleAssignment.app_user_id == user.app_user_id,
            UserRoleAssignment.role_id == role.role_id,
            UserRoleAssignment.scope_type == scope_type,
            UserRoleAssignment.scope_id == scope_id,
            UserRoleAssignment.revoked_at.is_(None),
        )
    )
    if exists is None:
        session.add(
            UserRoleAssignment(
                app_user_id=user.app_user_id,
                role_id=role.role_id,
                scope_type=scope_type,
                scope_id=scope_id,
                granted_by_user_id=user.app_user_id,
            )
        )


def main() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        roles = ensure_roles(session)

        admin = ensure_user(
            session,
            employee_number="1001",
            full_name_he="מיכל אדמין",
            full_name_en="Michal Admin",
            email="admin@damah.local",
            username="admin",
            password="admin123",
            language=LanguageCode.HE,
        )
        reviewer = ensure_user(
            session,
            employee_number="1002",
            full_name_he="רן בודק",
            full_name_en="Ran Reviewer",
            email="reviewer@damah.local",
            username="reviewer",
            password="reviewer123",
            language=LanguageCode.HE,
        )
        submitter = ensure_user(
            session,
            employee_number="1003",
            full_name_he="נועה מגישה",
            full_name_en="Noa Submitter",
            email="submitter@damah.local",
            username="submitter",
            password="submitter123",
            language=LanguageCode.HE,
        )
        group_admin = ensure_user(
            session,
            employee_number="1004",
            full_name_he="יואב קבוצה",
            full_name_en="Yoav Group",
            email="groupadmin@damah.local",
            username="groupadmin",
            password="groupadmin123",
            language=LanguageCode.EN,
        )
        ensure_role_assignment(session, user=admin, role=roles[RoleCode.ADMIN], scope_type=ScopeType.GLOBAL)
        ensure_role_assignment(session, user=admin, role=roles[RoleCode.REVIEWER], scope_type=ScopeType.GLOBAL)
        ensure_role_assignment(session, user=reviewer, role=roles[RoleCode.REVIEWER], scope_type=ScopeType.GLOBAL)
        ensure_role_assignment(session, user=submitter, role=roles[RoleCode.SUBMITTER], scope_type=ScopeType.GLOBAL)
        ensure_role_assignment(session, user=group_admin, role=roles[RoleCode.GROUP_ADMIN], scope_type=ScopeType.GLOBAL)

        if session.scalar(
            select(AuthIdentity).where(
                AuthIdentity.app_user_id == admin.app_user_id,
                AuthIdentity.auth_type == AuthType.SSO,
                AuthIdentity.external_subject == "stub-admin-subject",
                AuthIdentity.disabled_at.is_(None),
            )
        ) is None:
            session.add(
                AuthIdentity(
                    app_user_id=admin.app_user_id,
                    auth_type=AuthType.SSO,
                    external_subject="stub-admin-subject",
                    is_primary=False,
                    is_verified=True,
                )
            )

        group = session.scalar(select(AccessGroup).where(AccessGroup.group_name == "Finance Daily"))
        if group is None:
            group = AccessGroup(
                group_name="Finance Daily",
                group_description="Daily reconciliation workspace group",
                created_by_user_id=admin.app_user_id,
            )
            session.add(group)
            session.flush()

        for user, membership_role in (
            (admin, MembershipRole.GROUP_ADMIN),
            (reviewer, MembershipRole.MEMBER),
            (submitter, MembershipRole.MEMBER),
            (group_admin, MembershipRole.GROUP_ADMIN),
        ):
            membership = session.scalar(
                select(GroupMembership).where(
                    GroupMembership.access_group_id == group.access_group_id,
                    GroupMembership.app_user_id == user.app_user_id,
                    GroupMembership.membership_status == MembershipStatus.ACTIVE,
                )
            )
            if membership is None:
                session.add(
                    GroupMembership(
                        access_group_id=group.access_group_id,
                        app_user_id=user.app_user_id,
                        membership_role=membership_role,
                        membership_status=MembershipStatus.ACTIVE,
                        granted_by_user_id=admin.app_user_id,
                    )
                )

        access_code = session.scalar(select(AccessCode).where(AccessCode.issued_for_scope == "seed-group-creation"))
        if access_code is None:
            session.add(
                AccessCode(
                    code_value_hash=hash_access_code("seed-group-code"),
                    code_type=AccessCodeType.GROUP_CREATION,
                    issued_by_user_id=admin.app_user_id,
                    issued_for_scope="seed-group-creation",
                    max_uses=5,
                    use_count=0,
                    expires_at=datetime.now(UTC) + timedelta(days=365),
                )
            )

        template = session.scalar(select(Template).where(Template.template_code == "daily_reconciliation"))
        if template is None:
            template = Template(
                template_code="daily_reconciliation",
                template_name_he="פיוס יומי",
                template_name_en="Daily Reconciliation",
                template_status=TemplateStatus.ACTIVE,
                version_number=1,
                created_by_user_id=admin.app_user_id,
                field_definitions=[
                    TemplateFieldDefinition(
                        field_key="reported_amount",
                        field_label_he="סכום מדווח",
                        field_label_en="Reported Amount",
                        field_type=FieldType.NUMBER,
                        is_required=True,
                        submitter_editable=True,
                        reviewer_editable=False,
                        admin_editable=True,
                        display_order=1,
                        validation_rule_ref="min:0",
                    ),
                    TemplateFieldDefinition(
                        field_key="approved_amount",
                        field_label_he="סכום מאושר",
                        field_label_en="Approved Amount",
                        field_type=FieldType.NUMBER,
                        is_required=False,
                        submitter_editable=False,
                        reviewer_editable=True,
                        admin_editable=True,
                        display_order=2,
                        validation_rule_ref="compare:approved_amount<=reported_amount",
                    ),
                    TemplateFieldDefinition(
                        field_key="notes",
                        field_label_he="הערות",
                        field_label_en="Notes",
                        field_type=FieldType.TEXT,
                        is_required=False,
                        submitter_editable=True,
                        reviewer_editable=True,
                        admin_editable=True,
                        display_order=3,
                    ),
                ],
            )
            session.add(template)
            session.flush()

        workspace = session.scalar(select(Workspace).where(Workspace.workspace_title == "פיוס יומי 2026-04-08"))
        if workspace is None:
            workspace = Workspace(
                access_group_id=group.access_group_id,
                template_id=template.template_id,
                workspace_title="פיוס יומי 2026-04-08",
                business_date=date(2026, 4, 8),
                workspace_status=WorkspaceStatus.ACTIVE,
                created_by_user_id=admin.app_user_id,
            )
            session.add(workspace)
            session.flush()
            session.add(
                WorkspaceStatusHistory(
                    workspace_id=workspace.workspace_id,
                    from_status=None,
                    to_status=WorkspaceStatus.ACTIVE.value,
                    changed_by_user_id=admin.app_user_id,
                )
            )
            for user, role in (
                (submitter, ParticipantRole.SUBMITTER),
                (reviewer, ParticipantRole.REVIEWER),
                (admin, ParticipantRole.ADMIN),
            ):
                session.add(
                    WorkspaceParticipant(
                        workspace_id=workspace.workspace_id,
                        app_user_id=user.app_user_id,
                        participant_role=role,
                        assigned_by_user_id=admin.app_user_id,
                    )
                )

            line_item_open = LineItem(
                workspace_id=workspace.workspace_id,
                line_item_key="LI-001",
                line_item_title="בדיקת התאמה לכרטיס אשראי",
                line_item_status=LineItemStatus.OPEN,
                created_by_user_id=admin.app_user_id,
            )
            line_item_done = LineItem(
                workspace_id=workspace.workspace_id,
                line_item_key="LI-002",
                line_item_title="השוואת סכום סופי",
                line_item_status=LineItemStatus.DONE,
                created_by_user_id=admin.app_user_id,
            )
            session.add_all([line_item_open, line_item_done])
            session.flush()
            for item in (line_item_open, line_item_done):
                session.add(
                    LineItemStatusHistory(
                        line_item_id=item.line_item_id,
                        from_status=None,
                        to_status=item.line_item_status.value,
                        changed_by_user_id=admin.app_user_id,
                    )
                )

            revision1 = WorkspaceRevision(
                workspace_id=workspace.workspace_id,
                revision_number=1,
                created_by_user_id=submitter.app_user_id,
                revision_reason=RevisionReason.SUBMITTER_EDIT,
            )
            revision2 = WorkspaceRevision(
                workspace_id=workspace.workspace_id,
                revision_number=2,
                created_by_user_id=admin.app_user_id,
                revision_reason=RevisionReason.ADMIN_EDIT,
            )
            session.add_all([revision1, revision2])
            session.flush()

            payload_open = CurrentPayload(
                workspace_id=workspace.workspace_id,
                line_item_id=line_item_open.line_item_id,
                workspace_revision_id=revision1.workspace_revision_id,
                template_id=template.template_id,
                payload_json={"reported_amount": 1200, "approved_amount": 1500, "notes": "Mismatch requires clarification"},
                is_current=True,
            )
            payload_done = CurrentPayload(
                workspace_id=workspace.workspace_id,
                line_item_id=line_item_done.line_item_id,
                workspace_revision_id=revision2.workspace_revision_id,
                template_id=template.template_id,
                payload_json=None,
                is_current=True,
                payload_archived=True,
            )
            session.add_all([payload_open, payload_done])
            session.flush()

            artifact = Artifact(
                artifact_type=ArtifactType.PAYLOAD_SNAPSHOT,
                storage_uri="seed://payloads/li-002.json",
                file_name="li-002.json",
                mime_type="application/json",
                checksum="seed-checksum",
                file_size_bytes=128,
                created_by_user_id=admin.app_user_id,
            )
            session.add(artifact)
            session.flush()
            payload_done.payload_artifact_id = artifact.artifact_id
            payload_done.archived_at = datetime.now(UTC)

            clarification = ClarificationRequest(
                workspace_id=workspace.workspace_id,
                line_item_id=line_item_open.line_item_id,
                requested_by_user_id=reviewer.app_user_id,
                status=ClarificationStatus.ANSWERED,
                message="Please explain the discrepancy.",
                answered_at=datetime.now(UTC),
            )
            session.add(clarification)
            session.flush()
            session.add_all(
                [
                    Comment(
                        workspace_id=workspace.workspace_id,
                        line_item_id=line_item_open.line_item_id,
                        clarification_request_id=clarification.clarification_request_id,
                        author_user_id=reviewer.app_user_id,
                        visibility_type=CommentVisibilityType.SUBMITTER_VISIBLE,
                        comment_text="Please explain the discrepancy.",
                    ),
                    Comment(
                        workspace_id=workspace.workspace_id,
                        line_item_id=line_item_open.line_item_id,
                        clarification_request_id=clarification.clarification_request_id,
                        author_user_id=submitter.app_user_id,
                        visibility_type=CommentVisibilityType.SUBMITTER_VISIBLE,
                        comment_text="The amount includes one late invoice.",
                    ),
                    Comment(
                        workspace_id=workspace.workspace_id,
                        line_item_id=line_item_open.line_item_id,
                        author_user_id=reviewer.app_user_id,
                        visibility_type=CommentVisibilityType.INTERNAL_ONLY,
                        comment_text="Need admin confirmation before closing.",
                    ),
                ]
            )

            session.add(
                Recommendation(
                    line_item_id=line_item_done.line_item_id,
                    recommended_by_user_id=reviewer.app_user_id,
                    recommended_action=RecommendedAction.DONE,
                    recommended_final_value_json={"reported_amount": 980, "approved_amount": 980, "notes": "Approved"},
                    reason_text="Matches final settlement file.",
                )
            )
            session.add(
                FinalValue(
                    line_item_id=line_item_done.line_item_id,
                    source_workspace_revision_id=revision2.workspace_revision_id,
                    original_submitted_current_payload_id=payload_done.current_payload_id,
                    final_value_json={"reported_amount": 980, "approved_amount": 980, "notes": "Approved"},
                    override_reason=None,
                    approved_by_user_id=admin.app_user_id,
                    is_current=True,
                )
            )
            session.add(
                ValidationIssue(
                    workspace_id=workspace.workspace_id,
                    line_item_id=line_item_open.line_item_id,
                    workspace_revision_id=revision1.workspace_revision_id,
                    severity=ValidationSeverity.BLOCKING,
                    rule_code="compare:approved_amount<=reported_amount",
                    message_he="הסכום המאושר לא יכול להיות גדול מהסכום המדווח.",
                    message_en="Approved amount cannot exceed reported amount.",
                    status=ValidationStatus.OPEN,
                )
            )

        session.commit()


if __name__ == "__main__":
    main()
