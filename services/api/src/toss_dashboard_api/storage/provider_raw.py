from __future__ import annotations

import hashlib
import os
import re
import stat
import uuid
from dataclasses import dataclass
from pathlib import Path

from toss_dashboard_api.contracts.base import sha256_prefixed

_RAW_REF_PATTERN = re.compile(
    r"^provider-raw:sha256/(?P<prefix>[0-9a-f]{2})/(?P<digest>[0-9a-f]{64})$"
)


class ProviderRawStoreError(RuntimeError):
    """Safe raw-store failure without raw bytes or private paths."""


class ProviderRawStoreConflict(ProviderRawStoreError):
    """A supposedly immutable hash-addressed object did not match its digest."""


@dataclass(frozen=True)
class PersistedRaw:
    raw_content_hash: str
    raw_storage_ref: str
    created: bool


def _is_reparse_or_symlink(path: Path) -> bool:
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode):
        return True
    attributes = getattr(info, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(attributes & reparse_flag)


class ProviderRawStore:
    """Append-only, exact-byte, hash-addressed raw response storage."""

    def __init__(self, base_directory: Path) -> None:
        if not base_directory.is_absolute():
            raise ProviderRawStoreError("raw base directory must be an injected absolute path")
        self._base_directory = base_directory
        self._prepare_directory(base_directory)
        self._root = (base_directory / "sha256").resolve(strict=False)
        self._prepare_directory(self._root)
        if self._root.parent != base_directory.resolve(strict=True):
            raise ProviderRawStoreError("raw store root escaped its injected base directory")

    def persist(self, raw_bytes: bytes) -> PersistedRaw:
        if not isinstance(raw_bytes, bytes):
            raise ProviderRawStoreError("raw payload must be exact bytes")
        digest = hashlib.sha256(raw_bytes).hexdigest()
        prefix_directory = self._root / digest[:2]
        self._prepare_directory(prefix_directory)
        target = prefix_directory / f"{digest}.raw"
        raw_ref = f"provider-raw:sha256/{digest[:2]}/{digest}"

        if target.exists():
            self._verify_existing(target, digest, raw_bytes)
            return PersistedRaw(f"sha256:{digest}", raw_ref, False)

        temp = prefix_directory / f".{digest}.{uuid.uuid4().hex}.tmp"
        descriptor: int | None = None
        try:
            descriptor = os.open(temp, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(descriptor, "wb", closefd=True) as stream:
                descriptor = None
                stream.write(raw_bytes)
                stream.flush()
                os.fsync(stream.fileno())
            self._assert_regular_single_link(temp)
            try:
                self._publish_no_replace(temp, target)
            except FileExistsError:
                self._verify_existing(target, digest, raw_bytes)
                return PersistedRaw(f"sha256:{digest}", raw_ref, False)
            temp.unlink()
            self._assert_regular_single_link(target)
            self._fsync_directory(prefix_directory)
            return PersistedRaw(f"sha256:{digest}", raw_ref, True)
        except ProviderRawStoreError:
            raise
        except Exception as exc:
            raise ProviderRawStoreError("raw persistence failed before durable publish") from exc
        finally:
            if descriptor is not None:
                os.close(descriptor)
            try:
                temp.unlink(missing_ok=True)
            except OSError:
                pass

    def read(self, raw_storage_ref: str) -> bytes:
        target, expected_digest = self._resolve_ref(raw_storage_ref)
        self._assert_regular_single_link(target)
        payload = target.read_bytes()
        if hashlib.sha256(payload).hexdigest() != expected_digest:
            raise ProviderRawStoreConflict("raw object content does not match its immutable digest")
        return payload

    def verify(self, raw_storage_ref: str, raw_content_hash: str) -> None:
        payload = self.read(raw_storage_ref)
        if sha256_prefixed(payload) != raw_content_hash:
            raise ProviderRawStoreConflict("raw object does not match its manifest hash")

    def _resolve_ref(self, raw_storage_ref: str) -> tuple[Path, str]:
        match = _RAW_REF_PATTERN.fullmatch(raw_storage_ref)
        if match is None or match.group("prefix") != match.group("digest")[:2]:
            raise ProviderRawStoreError("raw storage reference is not an approved opaque reference")
        prefix_directory = self._root / match.group("prefix")
        target = prefix_directory / f"{match.group('digest')}.raw"
        if not prefix_directory.exists() or _is_reparse_or_symlink(prefix_directory):
            raise ProviderRawStoreError("raw object directory is unsafe")
        if not target.exists():
            raise ProviderRawStoreError("raw object is not durably published")
        if target.parent.resolve(strict=True) != prefix_directory.resolve(strict=True):
            raise ProviderRawStoreError("raw object escaped its hash-addressed directory")
        return target, match.group("digest")

    def _prepare_directory(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        current = directory
        while True:
            if _is_reparse_or_symlink(current):
                raise ProviderRawStoreError("raw store cannot use reparse or symbolic links")
            if current == current.parent:
                break
            current = current.parent

    @staticmethod
    def _assert_regular_single_link(path: Path) -> None:
        if _is_reparse_or_symlink(path):
            raise ProviderRawStoreError("raw object cannot be a reparse or symbolic link")
        info = path.stat()
        if not stat.S_ISREG(info.st_mode):
            raise ProviderRawStoreError("raw object must be a regular file")
        if info.st_nlink != 1:
            raise ProviderRawStoreError("raw object hard links are prohibited")

    def _verify_existing(self, target: Path, digest: str, expected_bytes: bytes) -> None:
        self._assert_regular_single_link(target)
        payload = target.read_bytes()
        if hashlib.sha256(payload).hexdigest() != digest or payload != expected_bytes:
            raise ProviderRawStoreConflict("existing raw object conflicts with immutable digest")

    @staticmethod
    def _publish_no_replace(temp: Path, target: Path) -> None:
        """Atomically publish a durable inode only when the target is absent."""
        os.link(temp, target)

    @staticmethod
    def _fsync_directory(directory: Path) -> None:
        if os.name == "nt":
            return
        descriptor = os.open(directory, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
