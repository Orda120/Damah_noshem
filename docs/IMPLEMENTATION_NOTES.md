# Implementation Notes

## Assumptions

1. `docs/API_SPEC.md` and `docs/CRITICAL_SEQUENCE_DIAGRAMS_AND_DATA_FLOWS.md` are referenced by the repo but are not present in the current checkout as of 2026-04-08. Implementation currently follows `docs/ERD.md` plus the explicit requirements in the task prompt.
2. The archive catalog is implemented in the same PostgreSQL database for local MVP development, but remains metadata-only and uses soft-reference semantics in the service layer.
3. `TemplateFieldDefinition.validation_rule_ref` is interpreted with a lightweight semicolon-delimited rule DSL for MVP. This supports required-if, primitive type checks, numeric bounds, and simple cross-field comparisons without introducing typed per-template tables.
4. The SSO flow is implemented as a local stub for MVP integration and testing. It distinguishes linked SSO identities, known-but-unlinked company people, and unknown identities without depending on a real external IdP yet.
5. Group creation is currently allowed for any authenticated enabled user who presents a valid group-creation access code.
6. Archive restore persists a real restore-request row with status tracking, but the operational restore worker still stops at audited request creation rather than automatically rehydrating payload data into the hot store.

## Deviations

1. The API surface is grouped by domain under `/api/v1/*` using FastAPI routers. Exact route naming is derived from the ERD and task requirements because the expected API spec file is missing.
2. The web app uses locale-prefixed routes (`/he`, `/en`) to enforce Hebrew-first UI plus RTL/LTR behavior from the beginning.
3. The first end-to-end editing flow is line-item-first. Workspace-level payload support remains modeled in the schema but is not the main UI path yet.
4. Artifact handling currently supports direct multipart upload plus explicit artifact-link creation. A presigned-upload-target/finalize pattern was not added because the expected API spec document is missing; the current direct-upload path is the active MVP contract.
