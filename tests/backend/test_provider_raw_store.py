from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from toss_dashboard_api.storage import provider_raw
from toss_dashboard_api.storage.provider_raw import (
    ProviderRawStore,
    ProviderRawStoreConflict,
    ProviderRawStoreError,
)


def test_raw_store_hashes_exact_received_bytes(workspace_tmp_path: Path) -> None:
    raw_bytes = b'{"b":2, "a":1}\r\n'
    persisted = ProviderRawStore(workspace_tmp_path / "raw").persist(raw_bytes)
    assert persisted.raw_content_hash == f"sha256:{hashlib.sha256(raw_bytes).hexdigest()}"


def test_raw_hash_is_not_reserialized_json_hash(workspace_tmp_path: Path) -> None:
    raw_bytes = b'{"b":2, "a":1}\r\n'
    canonical = json.dumps(json.loads(raw_bytes), sort_keys=True, separators=(",", ":")).encode()
    persisted = ProviderRawStore(workspace_tmp_path / "raw").persist(raw_bytes)
    assert persisted.raw_content_hash != f"sha256:{hashlib.sha256(canonical).hexdigest()}"


def test_duplicate_raw_bytes_are_verified_and_deduplicated(workspace_tmp_path: Path) -> None:
    store = ProviderRawStore(workspace_tmp_path / "raw")
    first = store.persist(b"same")
    second = store.persist(b"same")
    assert first.created is True
    assert second.created is False
    assert second.raw_storage_ref == first.raw_storage_ref
    assert store.read(first.raw_storage_ref) == b"same"


def test_existing_hash_path_with_different_bytes_fails_closed(workspace_tmp_path: Path) -> None:
    store = ProviderRawStore(workspace_tmp_path / "raw")
    persisted = store.persist(b"original")
    digest = persisted.raw_content_hash.removeprefix("sha256:")
    target = workspace_tmp_path / "raw" / "sha256" / digest[:2] / f"{digest}.raw"
    target.write_bytes(b"corrupt")
    with pytest.raises(ProviderRawStoreConflict, match="immutable digest"):
        store.persist(b"original")


@pytest.mark.parametrize(
    "unsafe_ref",
    [
        "provider-raw:sha256/../" + "0" * 64,
        "C:/private/raw.bin",
        "/absolute/raw.bin",
        "provider-raw:sha256/00/" + "1" * 64,
    ],
)
def test_raw_reader_rejects_traversal_absolute_and_mismatched_refs(
    workspace_tmp_path: Path, unsafe_ref: str
) -> None:
    store = ProviderRawStore(workspace_tmp_path / "raw")
    with pytest.raises(ProviderRawStoreError, match="opaque reference"):
        store.read(unsafe_ref)


def test_raw_store_rejects_relative_injected_base() -> None:
    with pytest.raises(ProviderRawStoreError, match="absolute"):
        ProviderRawStore(Path("relative/raw"))


def test_raw_store_rejects_reparse_or_symbolic_component(
    workspace_tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    base = workspace_tmp_path / "raw"
    base.mkdir()
    original = provider_raw._is_reparse_or_symlink

    def simulated_reparse(path: Path) -> bool:
        return path == base or original(path)

    monkeypatch.setattr(provider_raw, "_is_reparse_or_symlink", simulated_reparse)
    with pytest.raises(ProviderRawStoreError, match="reparse or symbolic"):
        ProviderRawStore(base)


def test_raw_reader_rejects_hard_linked_object(workspace_tmp_path: Path) -> None:
    store = ProviderRawStore(workspace_tmp_path / "raw")
    persisted = store.persist(b"hard-link-target")
    digest = persisted.raw_content_hash.removeprefix("sha256:")
    target = workspace_tmp_path / "raw" / "sha256" / digest[:2] / f"{digest}.raw"
    alias = workspace_tmp_path / "raw" / "linked.raw"
    os.link(target, alias)
    with pytest.raises(ProviderRawStoreError, match="hard links"):
        store.read(persisted.raw_storage_ref)


def test_temp_write_or_no_replace_failure_does_not_publish_object(
    workspace_tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = ProviderRawStore(workspace_tmp_path / "raw")

    def fail_publish(_source: Path, _target: Path) -> None:
        raise OSError("simulated no-replace failure")

    monkeypatch.setattr(ProviderRawStore, "_publish_no_replace", staticmethod(fail_publish))
    with pytest.raises(ProviderRawStoreError, match="before durable publish"):
        store.persist(b"not-published")
    assert list((workspace_tmp_path / "raw").rglob("*.raw")) == []
    assert list((workspace_tmp_path / "raw").rglob("*.tmp")) == []


def test_half_written_temp_file_is_not_readable_as_raw(workspace_tmp_path: Path) -> None:
    store = ProviderRawStore(workspace_tmp_path / "raw")
    temp = workspace_tmp_path / "raw" / "sha256" / "00"
    temp.mkdir()
    (temp / ("." + "0" * 64 + ".partial.tmp")).write_bytes(b"partial")
    with pytest.raises(ProviderRawStoreError, match="unsafe|regular|opaque|durably"):
        store.read("provider-raw:sha256/00/" + "0" * 64)


def test_atomic_publish_creates_only_final_hash_object(workspace_tmp_path: Path) -> None:
    store = ProviderRawStore(workspace_tmp_path / "raw")
    persisted = store.persist(b"published")
    assert store.read(persisted.raw_storage_ref) == b"published"
    assert list((workspace_tmp_path / "raw").rglob("*.tmp")) == []
    assert len(list((workspace_tmp_path / "raw").rglob("*.raw"))) == 1


def test_raw_failure_exception_does_not_embed_payload(
    workspace_tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = ProviderRawStore(workspace_tmp_path / "raw")
    sensitive_body = b"private-provider-body-marker"

    def fail_publish(_source: Path, _target: Path) -> None:
        raise OSError("safe simulated failure")

    monkeypatch.setattr(ProviderRawStore, "_publish_no_replace", staticmethod(fail_publish))
    with pytest.raises(ProviderRawStoreError) as captured:
        store.persist(sensitive_body)
    assert sensitive_body.decode() not in str(captured.value)
    assert sensitive_body.decode() not in repr(captured.value)


def test_competing_same_bytes_before_publish_deduplicates_without_overwrite(
    workspace_tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = ProviderRawStore(workspace_tmp_path / "raw")
    raw_bytes = b"competing-same"

    def publish_competitor(_temp: Path, target: Path) -> None:
        target.write_bytes(raw_bytes)
        raise FileExistsError("simulated competing writer")

    monkeypatch.setattr(ProviderRawStore, "_publish_no_replace", staticmethod(publish_competitor))
    persisted = store.persist(raw_bytes)
    assert persisted.created is False
    assert store.read(persisted.raw_storage_ref) == raw_bytes
    assert list((workspace_tmp_path / "raw").rglob("*.tmp")) == []


def test_competing_different_bytes_before_publish_fails_closed_without_overwrite(
    workspace_tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = ProviderRawStore(workspace_tmp_path / "raw")
    competing_bytes = b"competing-different"
    competing_target: Path | None = None

    def publish_competitor(_temp: Path, target: Path) -> None:
        nonlocal competing_target
        competing_target = target
        target.write_bytes(competing_bytes)
        raise FileExistsError("simulated competing writer")

    monkeypatch.setattr(ProviderRawStore, "_publish_no_replace", staticmethod(publish_competitor))
    with pytest.raises(ProviderRawStoreConflict, match="immutable digest"):
        store.persist(b"intended-bytes")
    assert competing_target is not None
    assert competing_target.read_bytes() == competing_bytes
    assert list((workspace_tmp_path / "raw").rglob("*.tmp")) == []


def test_no_replace_primitive_uses_hard_link_not_overwriting_rename(
    workspace_tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = ProviderRawStore(workspace_tmp_path / "raw")
    calls: list[tuple[Path, Path]] = []
    original_link = provider_raw.os.link

    def recorded_link(source: Path, target: Path) -> None:
        calls.append((source, target))
        original_link(source, target)

    monkeypatch.setattr(provider_raw.os, "link", recorded_link)
    persisted = store.persist(b"no-replace-primitive")
    assert persisted.created is True
    assert len(calls) == 1
    assert calls[0][0].suffix == ".tmp"
    assert calls[0][1].suffix == ".raw"
