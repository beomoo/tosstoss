from __future__ import annotations

import ctypes as ct
import re
from pathlib import Path
from typing import Any

import pytest

from toss_dashboard_api.reviewer import windows_owner as w
from toss_dashboard_api.reviewer.canonical import ReviewerError


def test_real_windows_owner_token_user_and_canonical_sid_hash(
    workspace_tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    api = w._Win32()
    first = w._verify_directory(workspace_tmp_path.resolve(), api)
    second = w._verify_directory(workspace_tmp_path.resolve(), api)
    assert re.fullmatch("sha256:[0-9a-f]{64}", first) and first == second
    assert caplog.text == ""


def test_real_opened_directory_must_match_expected(workspace_tmp_path: Path) -> None:
    api = w._Win32()
    handle = api.open_directory(workspace_tmp_path)
    try:
        with pytest.raises(ReviewerError, match="OWNER_FINAL_PATH_MISMATCH"):
            api.validate_directory(handle, workspace_tmp_path / "different")
    finally:
        api.kernel.CloseHandle(handle)


def test_non_windows_production_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(w.sys, "platform", "linux")
    with pytest.raises(ReviewerError, match="WINDOWS_REQUIRED"):
        w.verify_production_owner(w.canonical_database())


def test_noncanonical_db_and_caller_sid_rejected(workspace_tmp_path: Path) -> None:
    with pytest.raises(ReviewerError, match="NONCANONICAL_AUTHORITY_DATABASE"):
        w.verify_production_owner(workspace_tmp_path / "dashboard.db")
    with pytest.raises(TypeError):
        w.verify_production_owner(w.canonical_database(), os_owner_sid_hash="caller")  # type: ignore[call-arg]


@pytest.mark.parametrize(
    "failure,code",
    [
        ("reparse", "OWNER_DIRECTORY_REPARSE_REJECTED"),
        ("remote", "OWNER_REMOTE_VOLUME_REJECTED"),
        ("acl", "OWNER_PERSISTENT_ACL_REQUIRED"),
    ],
)
def test_controlled_win32_negative_adapter(
    workspace_tmp_path: Path, failure: str, code: str
) -> None:
    api = w._Win32()
    real = api.kernel

    def attributes(_handle: Any, _kind: int, target: Any, _length: int) -> int:
        ct.cast(target, ct.POINTER(w._AttributeTag)).contents.attributes = 0x410
        return 1

    def volume(
        _root: Any,
        _name: Any,
        _name_size: int,
        _serial: Any,
        _component: Any,
        flags: Any,
        _filesystem: Any,
        _size: int,
    ) -> int:
        ct.cast(flags, ct.POINTER(w.wt.DWORD)).contents.value = 0
        return 1

    class Adapter:
        def __getattr__(self, name: str) -> Any:
            if failure == "reparse" and name == "GetFileInformationByHandleEx":
                return attributes
            if failure == "remote" and name == "GetDriveTypeW":
                return lambda _root: 4
            if failure == "acl" and name == "GetVolumeInformationW":
                return volume
            return getattr(real, name)

    api.kernel = Adapter()
    with pytest.raises(ReviewerError, match=code):
        w._verify_directory(workspace_tmp_path, api)


def test_owner_mismatch_never_converts_sid(workspace_tmp_path: Path) -> None:
    api = w._Win32()
    real = api.security
    calls: list[str] = []

    class Adapter:
        def __getattr__(self, name: str) -> Any:
            if name == "EqualSid":
                return lambda _owner, _user: 0
            if name == "ConvertSidToStringSidW":
                return lambda *_args: calls.append("forbidden")
            return getattr(real, name)

    api.security = Adapter()
    with pytest.raises(ReviewerError, match="OWNER_TOKEN_USER_MISMATCH"):
        w._verify_directory(workspace_tmp_path, api)
    assert not calls
