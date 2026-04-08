from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings
from app.storage.azure import AzureBlobArtifactStorage
from app.storage.base import ArtifactStorage
from app.storage.filesystem import FilesystemArtifactStorage


@lru_cache
def get_storage() -> ArtifactStorage:
    settings = get_settings()
    if settings.storage_mode == "azure_blob":
        return AzureBlobArtifactStorage()
    return FilesystemArtifactStorage(settings.storage_base_path)
