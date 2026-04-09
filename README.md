# Damah_noshem

Internal daily-submission review and reconciliation app built with:

- `apps/api`: FastAPI, SQLAlchemy, Alembic
- `apps/web`: Next.js, React, TypeScript, Tailwind
- `packages/shared`: shared locale constants

The implementation follows `docs/ERD.md` plus the product requirements in this repository. The originally referenced `docs/API_SPEC.md` and `docs/CRITICAL_SEQUENCE_DIAGRAMS_AND_DATA_FLOWS.md` are still missing from the checkout, and the current assumptions are recorded in `docs/IMPLEMENTATION_NOTES.md`.

## What Exists

- Password-based auth with HTTP-only session cookie
- Stubbed SSO start/callback plus identity-linking-required and identity-link completion flows
- Centralized authorization with role, group, workspace, and optional access-policy checks
- Template and field-definition management in PostgreSQL
- Workspace, participant, and line-item lifecycle flows
- Revisioned JSON payload storage with optimistic concurrency
- Validation issues with blocking/warning severity
- Clarification, comment, recommendation, and final-value workflow
- Append-only final values and status histories
- Artifact upload, output generation, and archive stub-row flow
- Archive catalog search, restore request persistence, and restore-status lookup
- Hebrew-first web UI with English switch and RTL/LTR support
- Desktop-browser-only UI with explicit small-screen rejection instead of mobile navigation
- Seed/demo data plus backend and frontend smoke tests for critical flows

## Repository Layout

- `docs/`
- `apps/api/`
- `apps/web/`
- `packages/shared/`
- `infra/`
- `scripts/`

## Local Setup

1. Copy `.env.example` to `.env` if you want to override defaults.
2. Start the stack:

```bash
docker compose up --build
```

3. Open:

- Web: [http://localhost:3000/he/login](http://localhost:3000/he/login)
- API docs: [http://localhost:8001/docs](http://localhost:8001/docs)

The compose flow runs Alembic, seeds demo data, then starts the API and web servers.
The API host port defaults to `8001` to avoid collisions with local gateway or proxy services that often occupy `8000`.

## Demo Accounts

- `admin / admin123`
- `reviewer / reviewer123`
- `submitter / submitter123`
- `groupadmin / groupadmin123`

## Local Commands

Backend:

```bash
cd apps/api
python -m pip install -e .[dev]
alembic upgrade head
python -m app.db.seed
python -m pytest
uvicorn app.main:app --reload
```

Frontend:

```bash
npm install
npm run test --workspace @damah-noshem/web
npm run typecheck --workspace @damah-noshem/web
npm run lint --workspace @damah-noshem/web
npm run build --workspace @damah-noshem/web
npm run dev --workspace @damah-noshem/web
```

## Key API Areas

- `/api/v1/auth/*`
- `/api/v1/groups`
- `/api/v1/access-codes`
- `/api/v1/templates`
- `/api/v1/workspaces`
- `/api/v1/line-items/*`
- `/api/v1/output/*`
- `/api/v1/archive/*`
- `/api/v1/admin/*`

## Verification

Verified locally in this workspace:

- `python -m pytest` in `apps/api`
- `npm run test --workspace @damah-noshem/web`
- `npm run typecheck --workspace @damah-noshem/web`
- `npm run lint --workspace @damah-noshem/web`
- `npm run build --workspace @damah-noshem/web`
