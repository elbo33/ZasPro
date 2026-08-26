"""Storage interface. Local filesystem now; an S3 implementation slots in behind
the same protocol without touching callers (SPEC §3).
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Protocol

from zaspro.config import get_settings


class Storage(Protocol):
    def put(self, key: str, data: bytes) -> str: ...
    def put_file(self, key: str, path: Path) -> str: ...
    def get(self, key: str) -> bytes: ...
    def exists(self, key: str) -> bool: ...
    def url(self, key: str) -> str: ...


class LocalStorage:
    def __init__(self, root: Path | None = None) -> None:
        self.root = Path(root or get_settings().storage_root).resolve()

    def _path(self, key: str) -> Path:
        p = (self.root / key.lstrip("/")).resolve()
        if not str(p).startswith(str(self.root)):
            raise ValueError(f"key escapes storage root: {key!r}")
        return p

    def put(self, key: str, data: bytes) -> str:
        p = self._path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return key

    def put_file(self, key: str, path: Path) -> str:
        p = self._path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, p)
        return key

    def get(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def exists(self, key: str) -> bool:
        return self._path(key).is_file()

    def url(self, key: str) -> str:
        return self._path(key).as_uri()


def get_storage() -> Storage:
    return LocalStorage()
