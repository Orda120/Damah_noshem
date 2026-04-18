from __future__ import annotations

import hashlib
from pathlib import Path

from app.storage.base import ArtifactStorage, StoredArtifact


class FilesystemArtifactStorage(ArtifactStorage):
    def __init__(self, base_path: Path) -> None:
        self.base_path = base_path
        self.base_path.mkdir(parents=True, exist_ok=True)

    def write_bytes(self, *, relative_path: str, payload: bytes) -> StoredArtifact:
        target = self.base_path / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        checksum = hashlib.sha256(payload).hexdigest()
        return StoredArtifact(
            storage_uri=str(target),
            checksum=checksum,
            file_size_bytes=len(payload),
        )

    def read_bytes(self, *, storage_uri: str) -> bytes:
        return Path(storage_uri).read_bytes()
