"""Handle-based Windows owner boundary. No enrollment and no database writes."""

from __future__ import annotations

import ctypes as ct
import sys
from ctypes import wintypes as wt
from pathlib import Path
from typing import Any, ClassVar

import toss_dashboard_api

from .canonical import ReviewerError, digest


class _AttributeTag(ct.Structure):
    _fields_: ClassVar = [("attributes", wt.DWORD), ("tag", wt.DWORD)]


class _SidAttributes(ct.Structure):
    _fields_: ClassVar = [("sid", ct.c_void_p), ("attributes", wt.DWORD)]


class _Win32:
    """Private adapter seam; production always instantiates the real Win32 API."""

    kernel: ct.CDLL
    security: ct.CDLL

    def __init__(self) -> None:
        if sys.platform != "win32":
            raise ReviewerError("WINDOWS_REQUIRED")
        self.kernel = ct.WinDLL("kernel32", use_last_error=True)
        self.security = ct.WinDLL("advapi32", use_last_error=True)
        signatures: list[tuple[Any, str, Any, list[Any]]] = [
            (
                self.kernel,
                "CreateFileW",
                wt.HANDLE,
                [wt.LPCWSTR, wt.DWORD, wt.DWORD, ct.c_void_p, wt.DWORD, wt.DWORD, wt.HANDLE],
            ),
            (self.kernel, "CloseHandle", wt.BOOL, [wt.HANDLE]),
            (
                self.kernel,
                "GetFileInformationByHandleEx",
                wt.BOOL,
                [wt.HANDLE, ct.c_int, ct.c_void_p, wt.DWORD],
            ),
            (
                self.kernel,
                "GetFinalPathNameByHandleW",
                wt.DWORD,
                [wt.HANDLE, wt.LPWSTR, wt.DWORD, wt.DWORD],
            ),
            (self.kernel, "GetVolumePathNameW", wt.BOOL, [wt.LPCWSTR, wt.LPWSTR, wt.DWORD]),
            (self.kernel, "GetDriveTypeW", wt.UINT, [wt.LPCWSTR]),
            (
                self.kernel,
                "GetVolumeInformationW",
                wt.BOOL,
                [
                    wt.LPCWSTR,
                    wt.LPWSTR,
                    wt.DWORD,
                    ct.c_void_p,
                    ct.c_void_p,
                    ct.POINTER(wt.DWORD),
                    wt.LPWSTR,
                    wt.DWORD,
                ],
            ),
            (
                self.kernel,
                "CompareStringOrdinal",
                ct.c_int,
                [wt.LPCWSTR, ct.c_int, wt.LPCWSTR, ct.c_int, wt.BOOL],
            ),
            (self.kernel, "GetCurrentProcess", wt.HANDLE, []),
            (self.kernel, "LocalFree", ct.c_void_p, [ct.c_void_p]),
            (self.kernel, "CreateDirectoryW", wt.BOOL, [wt.LPCWSTR, ct.c_void_p]),
            (
                self.security,
                "GetSecurityInfo",
                wt.DWORD,
                [
                    wt.HANDLE,
                    ct.c_int,
                    wt.DWORD,
                    ct.POINTER(ct.c_void_p),
                    ct.c_void_p,
                    ct.c_void_p,
                    ct.c_void_p,
                    ct.POINTER(ct.c_void_p),
                ],
            ),
            (self.security, "IsValidSid", wt.BOOL, [ct.c_void_p]),
            (self.security, "EqualSid", wt.BOOL, [ct.c_void_p, ct.c_void_p]),
            (
                self.security,
                "OpenProcessToken",
                wt.BOOL,
                [wt.HANDLE, wt.DWORD, ct.POINTER(wt.HANDLE)],
            ),
            (
                self.security,
                "GetTokenInformation",
                wt.BOOL,
                [wt.HANDLE, ct.c_int, ct.c_void_p, wt.DWORD, ct.POINTER(wt.DWORD)],
            ),
            (
                self.security,
                "ConvertSidToStringSidW",
                wt.BOOL,
                [ct.c_void_p, ct.POINTER(ct.c_void_p)],
            ),
        ]
        for library, name, result, arguments in signatures:
            function = getattr(library, name)
            function.restype, function.argtypes = result, arguments

    def same_path(self, left: str, right: str) -> bool:
        # Win32 counts UTF-16 code units, unlike Python's code-point len().
        # Null-terminated comparison covers non-BMP path components exactly.
        return bool(self.kernel.CompareStringOrdinal(left, -1, right, -1, True) == 2)

    def open_directory(self, path: Path) -> Any:
        handle = self.kernel.CreateFileW(str(path), 0x20000, 7, None, 3, 0x02200000, None)
        if handle in (None, ct.c_void_p(-1).value):
            raise ReviewerError("OWNER_DIRECTORY_OPEN_FAILED")
        return handle

    def validate_directory(self, handle: Any, path: Path) -> None:
        attributes = _AttributeTag()
        if not self.kernel.GetFileInformationByHandleEx(
            handle, 9, ct.byref(attributes), ct.sizeof(attributes)
        ):
            raise ReviewerError("OWNER_DIRECTORY_QUERY_FAILED")
        if attributes.attributes & 0x400 or not attributes.attributes & 0x10:
            raise ReviewerError("OWNER_DIRECTORY_REPARSE_REJECTED")
        final = ct.create_unicode_buffer(32768)
        size = self.kernel.GetFinalPathNameByHandleW(handle, final, len(final), 0)
        if not size or size >= len(final):
            raise ReviewerError("OWNER_FINAL_PATH_FAILED")
        name = final.value
        if name.startswith("\\\\?\\UNC\\") or (
            name.startswith("\\\\") and not name.startswith("\\\\?\\")
        ):
            raise ReviewerError("OWNER_REMOTE_VOLUME_REJECTED")
        name = name.removeprefix("\\\\?\\")
        if not self.same_path(name, str(path)):
            raise ReviewerError("OWNER_FINAL_PATH_MISMATCH")
        volume = ct.create_unicode_buffer(32768)
        if not self.kernel.GetVolumePathNameW(name, volume, len(volume)):
            raise ReviewerError("OWNER_VOLUME_QUERY_FAILED")
        if self.kernel.GetDriveTypeW(volume.value) not in (2, 3, 6):
            raise ReviewerError("OWNER_REMOTE_VOLUME_REJECTED")
        flags = wt.DWORD()
        if (
            not self.kernel.GetVolumeInformationW(
                volume.value, None, 0, None, None, ct.byref(flags), None, 0
            )
            or not flags.value & 8
        ):
            raise ReviewerError("OWNER_PERSISTENT_ACL_REQUIRED")

    def owner_hash(self, handle: Any) -> str:
        owner, descriptor, text_sid = ct.c_void_p(), ct.c_void_p(), ct.c_void_p()
        token = wt.HANDLE()
        try:
            if (
                self.security.GetSecurityInfo(
                    handle, 1, 1, ct.byref(owner), None, None, None, ct.byref(descriptor)
                )
                != 0
            ):
                raise ReviewerError("OWNER_SECURITY_QUERY_FAILED")
            if not owner.value or not self.security.IsValidSid(owner):
                raise ReviewerError("OWNER_SID_INVALID")
            if not self.security.OpenProcessToken(
                self.kernel.GetCurrentProcess(), 8, ct.byref(token)
            ):
                raise ReviewerError("PROCESS_TOKEN_OPEN_FAILED")
            length = wt.DWORD()
            self.security.GetTokenInformation(token, 1, None, 0, ct.byref(length))
            if (
                sys.platform != "win32"
                or ct.get_last_error() != 122
                or not ct.sizeof(_SidAttributes) <= length.value <= 65536
            ):
                raise ReviewerError("TOKEN_USER_QUERY_FAILED")
            buffer = ct.create_string_buffer(length.value)
            if not self.security.GetTokenInformation(token, 1, buffer, length, ct.byref(length)):
                raise ReviewerError("TOKEN_USER_QUERY_FAILED")
            sid = ct.cast(buffer, ct.POINTER(_SidAttributes)).contents.sid
            if not sid or not self.security.IsValidSid(sid):
                raise ReviewerError("TOKEN_USER_SID_INVALID")
            if not self.security.EqualSid(owner, sid):
                raise ReviewerError("OWNER_TOKEN_USER_MISMATCH")
            if (
                not self.security.ConvertSidToStringSidW(sid, ct.byref(text_sid))
                or not text_sid.value
            ):
                raise ReviewerError("TOKEN_USER_TEXT_FAILED")
            return digest(ct.wstring_at(text_sid).encode("utf-8", errors="strict"))
        finally:
            if text_sid.value:
                self.kernel.LocalFree(text_sid)
            if descriptor.value:
                self.kernel.LocalFree(descriptor)
            if token.value:
                self.kernel.CloseHandle(token)


def _verify_directory(path: Path, api: _Win32) -> str:
    handle = api.open_directory(path)
    try:
        api.validate_directory(handle, path)
        return api.owner_hash(handle)
    finally:
        api.kernel.CloseHandle(handle)


def canonical_database() -> Path:
    if toss_dashboard_api.__file__ is None:
        raise ReviewerError("PRODUCTION_ROOT_UNAVAILABLE")
    return Path(toss_dashboard_api.__file__).resolve().parents[4] / "var" / "dashboard.db"


def verify_production_owner(database: Path) -> str:
    """No injectable owner, adapter, platform, root, or bypass parameter."""
    api = _Win32()
    expected = canonical_database()
    try:
        # Reject a junction at var before resolve() can erase its identity.
        directory = expected.parent
        if directory.is_symlink() or directory.is_junction():
            raise ReviewerError("OWNER_DIRECTORY_REPARSE_REJECTED")
        resolved = directory.resolve(strict=False) / "dashboard.db"
        if not database.is_absolute() or not api.same_path(str(database.resolve()), str(resolved)):
            raise ReviewerError("NONCANONICAL_AUTHORITY_DATABASE")
        if not directory.exists():
            root = directory.parent.resolve(strict=True)
            _verify_directory(root, api)
            if not api.kernel.CreateDirectoryW(str(root / "var"), None):
                raise ReviewerError("OWNER_DIRECTORY_CREATE_FAILED")
        return _verify_directory(directory.resolve(strict=True), api)
    except OSError:
        raise ReviewerError("OWNER_BOUNDARY_FAILED") from None
