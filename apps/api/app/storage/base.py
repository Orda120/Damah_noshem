from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True)
class StoredArtifact:
    storage_uri: str
    checksum: str
    file_size_bytes: int


class ArtifactStorage(Protocol):
    def write_bytes(self, *, relative_path: str, payload: bytes) -> StoredArtifact: ...

    def read_bytes(self, *, storage_uri: str) -> bytes: ...
