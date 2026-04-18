from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.db.enums import FieldType, ValidationSeverity, ValidationStatus
from app.db.models import LineItem, Template, TemplateFieldDefinition, ValidationIssue, WorkspaceRevision


@dataclass(slots=True)
class ValidationResult:
    rule_code: str
    severity: ValidationSeverity
    message_he: str
    message_en: str


def _is_empty(value: object) -> bool:
    return value in (None, "", [], {})


def _coerce_number(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value))
    except ValueError:
        return None


def validate_payload(
    *,
    template: Template,
    payload_json: dict,
) -> list[ValidationResult]:
    issues: list[ValidationResult] = []
    fields_by_key = {field.field_key: field for field in template.field_definitions}

    for field in template.field_definitions:
        value = payload_json.get(field.field_key)
        if field.is_required and _is_empty(value):
            issues.append(
                ValidationResult(
                    rule_code=f"required:{field.field_key}",
                    severity=ValidationSeverity.BLOCKING,
                    message_he=f"יש למלא את השדה {field.field_label_he}.",
                    message_en=f"The field {field.field_label_en} is required.",
                )
            )

        if not _is_empty(value):
            if field.field_type == FieldType.NUMBER and _coerce_number(value) is None:
                issues.append(
                    ValidationResult(
                        rule_code=f"type:number:{field.field_key}",
                        severity=ValidationSeverity.BLOCKING,
                        message_he=f"השדה {field.field_label_he} חייב להיות מספר.",
                        message_en=f"The field {field.field_label_en} must be a number.",
                    )
                )

        if field.validation_rule_ref:
            for clause in [part.strip() for part in field.validation_rule_ref.split(";") if part.strip()]:
                if clause.startswith("required_if:"):
                    _, expr = clause.split(":", 1)
                    other_field, expected = expr.split("=", 1)
                    if str(payload_json.get(other_field)) == expected and _is_empty(value):
                        issues.append(
                            ValidationResult(
                                rule_code=f"required_if:{field.field_key}:{other_field}",
                                severity=ValidationSeverity.BLOCKING,
                                message_he=f"השדה {field.field_label_he} נדרש כאשר {other_field}={expected}.",
                                message_en=(
                                    f"The field {field.field_label_en} is required when {other_field}={expected}."
                                ),
                            )
                        )
                elif clause.startswith("min:"):
                    limit = float(clause.split(":", 1)[1])
                    numeric_value = _coerce_number(value)
                    if numeric_value is not None and numeric_value < limit:
                        issues.append(
                            ValidationResult(
                                rule_code=f"min:{field.field_key}",
                                severity=ValidationSeverity.WARNING,
                                message_he=f"הערך בשדה {field.field_label_he} קטן מהמינימום {limit}.",
                                message_en=f"The value in {field.field_label_en} is lower than {limit}.",
                            )
                        )
                elif clause.startswith("compare:"):
                    _, expr = clause.split(":", 1)
                    left_field, operator, right_field = None, None, None
                    for candidate in ("<=", ">=", "=="):
                        if candidate in expr:
                            left_field, right_field = expr.split(candidate, 1)
                            operator = candidate
                            break
                    if left_field and right_field and operator:
                        left = payload_json.get(left_field)
                        right = payload_json.get(right_field)
                        if operator == "<=" and left is not None and right is not None and left > right:
                            right_label = fields_by_key.get(right_field, field).field_label_en
                            issues.append(
                                ValidationResult(
                                    rule_code=f"compare:{left_field}{operator}{right_field}",
                                    severity=ValidationSeverity.BLOCKING,
                                    message_he=f"השדה {field.field_label_he} חייב להיות קטן או שווה ל-{right_field}.",
                                    message_en=f"{field.field_label_en} must be <= {right_label}.",
                                )
                            )

    return issues


def replace_validation_issues(
    session: Session,
    *,
    template: Template,
    workspace_id,
    line_item_id,
    workspace_revision: WorkspaceRevision,
    payload_json: dict,
) -> list[ValidationIssue]:
    session.execute(
        update(ValidationIssue)
        .where(
            ValidationIssue.workspace_id == workspace_id,
            ValidationIssue.line_item_id == line_item_id,
            ValidationIssue.status == ValidationStatus.OPEN,
        )
        .values(status=ValidationStatus.RESOLVED)
    )
    created: list[ValidationIssue] = []
    for issue in validate_payload(template=template, payload_json=payload_json):
        row = ValidationIssue(
            workspace_id=workspace_id,
            line_item_id=line_item_id,
            workspace_revision_id=workspace_revision.workspace_revision_id,
            severity=issue.severity,
            rule_code=issue.rule_code,
            message_he=issue.message_he,
            message_en=issue.message_en,
            status=ValidationStatus.OPEN,
        )
        session.add(row)
        created.append(row)
    session.flush()
    return created


def get_open_blocking_issues(session: Session, *, line_item: LineItem) -> list[ValidationIssue]:
    return session.scalars(
        select(ValidationIssue).where(
            ValidationIssue.line_item_id == line_item.line_item_id,
            ValidationIssue.status == ValidationStatus.OPEN,
            ValidationIssue.severity == ValidationSeverity.BLOCKING,
        )
    ).all()
