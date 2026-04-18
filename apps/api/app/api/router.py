from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import admin, archive, artifacts, auth, groups, output, review, templates, workspaces

router = APIRouter()
router.include_router(auth.router)
router.include_router(groups.router)
router.include_router(templates.router)
router.include_router(workspaces.router)
router.include_router(review.router)
router.include_router(artifacts.router)
router.include_router(output.router)
router.include_router(archive.router)
router.include_router(admin.router)
