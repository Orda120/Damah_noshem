from __future__ import annotations

from app.storage.base import ArtifactStorage, StoredArtifact


class AzureBlobArtifactStorage(ArtifactStorage):
    def write_bytes(self, *, relative_path: str, payload: bytes) -> StoredArtifact:
        raise NotImplementedError("Azure Blob storage adapter is not configured in local MVP mode.")

    def read_bytes(self, *, storage_uri: str) -> bytes:
        raise NotImplementedError("Azure Blob storage adapter is not configured in local MVP mode.")
