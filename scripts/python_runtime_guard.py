from __future__ import annotations

import _socket
import ipaddress
import os
import runpy
import socket
import stat
import subprocess
import sys
import threading
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import NoReturn

BLOCKED_NETWORK_CODE = "ERR_OFFLINE_NON_LOOPBACK"
BLOCKED_PROCESS_CODE = "ERR_OFFLINE_PROCESS_CREATION"
_INTERNET_FAMILIES = {socket.AF_INET, socket.AF_INET6}
_AF_UNIX = getattr(socket, "AF_UNIX", None)
_NATIVE_SOCKET_TYPE = _socket.socket
_IP_ADDRESS = ipaddress.ip_address
_LIST2CMDLINE = subprocess.list2cmdline
_GUARD_PATH = Path(__file__).resolve(strict=True)
_REPO_ROOT = _GUARD_PATH.parent.parent
_VENV_ROOT = _REPO_ROOT / ".venv"
_SECRET_SCAN_DRIVER = _GUARD_PATH.with_name("secret_scan_driver.py")
_UVICORN_LOG_CONFIG = _REPO_ROOT / "services" / "api" / "uvicorn_log_config.json"
_RUFF_EXECUTABLE = _VENV_ROOT / "Scripts" / "ruff.exe"
_APPROVED_UVICORN_APPLICATIONS = frozenset(
    {
        "tests.backend.uvicorn_canary_app:app",
        "toss_dashboard_api.main:app",
    }
)
_APPROVED_RUFF_ARGUMENTS = (
    (
        "format",
        "--check",
        "--no-cache",
        "services/api/src",
        "tests/backend",
        "scripts/python_runtime_guard.py",
        "scripts/secret_scan_driver.py",
    ),
    (
        "check",
        "--no-cache",
        "services/api/src",
        "tests/backend",
        "scripts/python_runtime_guard.py",
        "scripts/secret_scan_driver.py",
    ),
)
_PROCESS_CREATION_EVENTS = frozenset(
    {
        "os.exec",
        "os.posix_spawn",
        "os.spawn",
        "os.startfile",
        "os.startfile/2",
        "os.system",
        "pty.spawn",
    }
)


class OfflineNetworkError(OSError):
    """Raised before a non-loopback Python network operation can start."""

    code = BLOCKED_NETWORK_CODE


class OfflineProcessCreationError(PermissionError):
    """Raised before an unapproved child process can be created."""

    code = BLOCKED_PROCESS_CODE


def _blocked(api_name: str, _target: object) -> NoReturn:
    raise OfflineNetworkError(f"Blocked non-loopback {api_name} during offline Phase 1 checks.")


def _blocked_process(api_name: str) -> NoReturn:
    raise OfflineProcessCreationError(
        f"Blocked {api_name} process creation during offline Phase 1 checks."
    )


def _normalize_host(value: object) -> str | None:
    if isinstance(value, bytes):
        try:
            host = bytes.decode(value, "ascii", errors="strict")
        except UnicodeDecodeError:
            return None
    elif isinstance(value, str):
        host = str.__str__(value)
    else:
        return None
    host = str.lower(str.strip(host))
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]
    if host.endswith("."):
        host = host[:-1]
    return host


def _is_normalized_loopback_host(host: str) -> bool:
    if host == "localhost":
        return True
    try:
        address = _IP_ADDRESS(host)
    except ValueError:
        return False
    if address.is_loopback:
        return True
    mapped = getattr(address, "ipv4_mapped", None)
    return mapped is not None and mapped.is_loopback


def _assert_loopback_host(value: object, api_name: str) -> str:
    host = _normalize_host(value)
    if host is None or not _is_normalized_loopback_host(host):
        _blocked(api_name, value)
    return host


def _snapshot_tuple(value: object, api_name: str) -> tuple[object, ...]:
    if not isinstance(value, tuple):
        _blocked(api_name, value)
    length = tuple.__len__(value)
    return tuple(tuple.__getitem__(value, index) for index in range(length))


def _snapshot_integer(value: object, api_name: str) -> int:
    if not isinstance(value, int):
        _blocked(api_name, value)
    return int.__index__(value)


def _snapshot_port(value: object, api_name: str) -> int | str | bytes:
    if isinstance(value, int):
        return int.__index__(value)
    if isinstance(value, str):
        return str.__str__(value)
    if isinstance(value, bytes):
        return b"".join((value,))
    _blocked(api_name, value)


def _snapshot_host_port_address(
    address: object,
    api_name: str,
) -> tuple[object, ...]:
    items = _snapshot_tuple(address, api_name)
    if len(items) != 2:
        _blocked(api_name, address)
    return (
        _assert_loopback_host(items[0], api_name),
        _snapshot_port(items[1], api_name),
    )


def _snapshot_nameinfo_address(
    address: object,
    api_name: str,
) -> tuple[object, ...]:
    items = _snapshot_tuple(address, api_name)
    if len(items) not in {2, 3, 4}:
        _blocked(api_name, address)
    snapshot: list[object] = [
        _assert_loopback_host(items[0], api_name),
        _snapshot_port(items[1], api_name),
    ]
    snapshot.extend(_snapshot_integer(value, api_name) for value in items[2:])
    return tuple(snapshot)


def _snapshot_socket_address(
    socket_object: object,
    address: object,
    api_name: str,
) -> str | bytes | tuple[object, ...]:
    if not isinstance(socket_object, _NATIVE_SOCKET_TYPE):
        _blocked(api_name, f"unexpected socket object: {type(socket_object).__name__}")
    family = _NATIVE_SOCKET_TYPE.family.__get__(socket_object, _NATIVE_SOCKET_TYPE)
    if _AF_UNIX is not None and family == _AF_UNIX:
        if isinstance(address, str):
            return str.__str__(address)
        if isinstance(address, bytes):
            return b"".join((address,))
        _blocked(api_name, address)
    if family not in _INTERNET_FAMILIES:
        _blocked(api_name, address)
    items = _snapshot_tuple(address, api_name)
    expected_lengths = {2} if family == socket.AF_INET else {2, 3, 4}
    if len(items) not in expected_lengths:
        _blocked(api_name, address)
    snapshot: list[object] = [
        _assert_loopback_host(items[0], api_name),
        _snapshot_port(items[1], api_name),
    ]
    snapshot.extend(_snapshot_integer(value, api_name) for value in items[2:])
    return tuple(snapshot)


_original_connect = socket.socket.connect
_original_connect_ex = socket.socket.connect_ex
_original_bind = socket.socket.bind
_original_sendto = socket.socket.sendto
_original_create_connection = socket.create_connection
_original_getaddrinfo = socket.getaddrinfo
_original_gethostbyname = socket.gethostbyname
_original_gethostbyname_ex = socket.gethostbyname_ex
_original_gethostbyaddr = socket.gethostbyaddr
_original_getnameinfo = socket.getnameinfo


def _guarded_connect(self: socket.socket, address: object) -> None:
    snapshot = _snapshot_socket_address(self, address, "socket.connect")
    return _original_connect(self, snapshot)


def _guarded_connect_ex(self: socket.socket, address: object) -> int:
    snapshot = _snapshot_socket_address(self, address, "socket.connect_ex")
    return _original_connect_ex(self, snapshot)


def _guarded_bind(self: socket.socket, address: object) -> None:
    snapshot = _snapshot_socket_address(self, address, "socket.bind")
    return _original_bind(self, snapshot)


def _guarded_sendto(self: socket.socket, data: object, *args: object) -> int:
    if not args:
        _blocked("socket.sendto", "implicit destination")
    snapshot = _snapshot_socket_address(self, args[-1], "socket.sendto")
    return _original_sendto(self, data, *args[:-1], snapshot)


def _guarded_create_connection(
    address: tuple[object, object],
    *args: object,
    **kwargs: object,
) -> socket.socket:
    snapshot = _snapshot_host_port_address(address, "socket.create_connection")
    return _original_create_connection(snapshot, *args, **kwargs)


def _guarded_getaddrinfo(host: object, *args: object, **kwargs: object) -> list[tuple]:
    snapshot = _assert_loopback_host(host, "socket.getaddrinfo")
    results = _original_getaddrinfo(snapshot, *args, **kwargs)
    for family, _, _, _, socket_address in results:
        if family in _INTERNET_FAMILIES:
            if not isinstance(socket_address, tuple) or not socket_address:
                _blocked("socket.getaddrinfo.result", socket_address)
            _assert_loopback_host(socket_address[0], "socket.getaddrinfo.result")
    return results


def _guarded_gethostbyname(host: object) -> str:
    snapshot = _assert_loopback_host(host, "socket.gethostbyname")
    result = _original_gethostbyname(snapshot)
    _assert_loopback_host(result, "socket.gethostbyname.result")
    return result


def _guarded_gethostbyname_ex(host: object) -> tuple[str, list[str], list[str]]:
    snapshot = _assert_loopback_host(host, "socket.gethostbyname_ex")
    name, aliases, addresses = _original_gethostbyname_ex(snapshot)
    for address in addresses:
        _assert_loopback_host(address, "socket.gethostbyname_ex.result")
    return name, aliases, addresses


def _guarded_gethostbyaddr(address: object) -> tuple[str, list[str], list[str]]:
    snapshot = _assert_loopback_host(address, "socket.gethostbyaddr")
    return _original_gethostbyaddr(snapshot)


def _guarded_getnameinfo(socket_address: tuple, flags: int) -> tuple[str, str]:
    snapshot = _snapshot_nameinfo_address(socket_address, "socket.getnameinfo")
    return _original_getnameinfo(snapshot, flags)


def _approved_guarded_uvicorn_argv(application: str, port: int) -> list[str]:
    return [
        sys.executable,
        "-I",
        "-B",
        "-S",
        str(_GUARD_PATH),
        "--module",
        "uvicorn",
        "--",
        application,
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--no-access-log",
        "--log-config",
        str(_UVICORN_LOG_CONFIG),
    ]


def _is_approved_guarded_uvicorn_child(arguments: tuple[object, ...]) -> bool:
    if len(arguments) != 4:
        return False
    executable, command_line, working_directory, _environment = arguments
    if (
        type(executable) is not str
        or executable != sys.executable
        or type(command_line) is not str
        or type(working_directory) is not str
        or working_directory != str(_REPO_ROOT)
    ):
        return False

    suffix = _LIST2CMDLINE(["--no-access-log", "--log-config", str(_UVICORN_LOG_CONFIG)])
    for application in _APPROVED_UVICORN_APPLICATIONS:
        prefix = _LIST2CMDLINE(_approved_guarded_uvicorn_argv(application, 1)[:-4])
        marker = prefix + " "
        ending = " " + suffix
        if not command_line.startswith(marker) or not command_line.endswith(ending):
            continue
        port_text = command_line[len(marker) : -len(ending)]
        if (
            port_text.isascii()
            and port_text.isdecimal()
            and str(int(port_text)) == port_text
            and 1 <= int(port_text) <= 65535
        ):
            return True
    return False


def _is_approved_ruff_child(arguments: tuple[object, ...]) -> bool:
    if len(arguments) != 4:
        return False
    executable, command_line, working_directory, environment = arguments
    if (
        executable is not None
        or type(command_line) is not str
        or working_directory is not None
        or environment is not None
    ):
        return False
    try:
        if Path.cwd().resolve(strict=True) != _REPO_ROOT:
            return False
    except OSError:
        return False
    return any(
        command_line == _LIST2CMDLINE([str(_RUFF_EXECUTABLE), *argument_list])
        for argument_list in _APPROVED_RUFF_ARGUMENTS
    )


def _audit_runtime(event: str, arguments: tuple[object, ...]) -> None:
    if event == "subprocess.Popen":
        if _is_approved_guarded_uvicorn_child(arguments) or _is_approved_ruff_child(arguments):
            return
        _blocked_process(event)
    if event in _PROCESS_CREATION_EVENTS:
        _blocked_process(event)
    if event in {"socket.connect", "socket.bind", "socket.sendto"}:
        if len(arguments) < 2:
            _blocked(event, arguments)
        _snapshot_socket_address(arguments[0], arguments[-1], event)
        return
    if event == "socket.getaddrinfo" and arguments:
        _assert_loopback_host(arguments[0], event)
        return
    if event in {"socket.gethostbyname", "socket.gethostbyaddr"} and arguments:
        _assert_loopback_host(arguments[0], event)
        return
    if event == "socket.getnameinfo" and arguments:
        _snapshot_nameinfo_address(arguments[0], event)


def _install_guard() -> None:
    if sys.flags.isolated != 1 or not sys.dont_write_bytecode or sys.flags.no_site != 1:
        raise RuntimeError("The Python runtime guard requires -I -B -S.")
    sys.addaudithook(_audit_runtime)
    socket.socket.connect = _guarded_connect
    socket.socket.connect_ex = _guarded_connect_ex
    socket.socket.bind = _guarded_bind
    socket.socket.sendto = _guarded_sendto
    socket.create_connection = _guarded_create_connection
    socket.getaddrinfo = _guarded_getaddrinfo
    socket.gethostbyname = _guarded_gethostbyname
    socket.gethostbyname_ex = _guarded_gethostbyname_ex
    socket.gethostbyaddr = _guarded_gethostbyaddr
    socket.getnameinfo = _guarded_getnameinfo


def _activate_guarded_site() -> None:
    # -S prevents executable .pth files and sitecustomize from running before
    # the immutable audit hook is installed. Calling site.main() afterwards
    # restores this repository's venv and editable source paths under the guard.
    import site

    site.main()
    try:
        active_prefix = Path(sys.prefix).resolve(strict=True)
        active_executable = Path(sys.executable).resolve(strict=True)
        expected_venv = _VENV_ROOT.resolve(strict=True)
    except OSError as error:
        raise RuntimeError("The guarded Python virtual environment is invalid.") from error
    if (
        active_prefix != expected_venv
        or active_executable.parent.parent != expected_venv
        or site.ENABLE_USER_SITE is not False
    ):
        raise RuntimeError("The guarded Python runtime did not activate the exact repository venv.")


def _assert_self_test_blocked(
    label: str,
    operation: Callable[[], object],
) -> None:
    try:
        operation()
    except OfflineNetworkError as error:
        if error.code != BLOCKED_NETWORK_CODE:
            raise AssertionError(f"The {label} canary emitted an unexpected error code.") from error
    except OSError as error:
        raise AssertionError(f"The {label} canary reached the operating system.") from error
    else:
        raise AssertionError(f"The Python guard allowed the {label} canary.")


def _assert_self_test_process_blocked(
    label: str,
    operation: Callable[[], object],
) -> None:
    try:
        operation()
    except OfflineProcessCreationError as error:
        if error.code != BLOCKED_PROCESS_CODE:
            raise AssertionError(f"The {label} canary emitted an unexpected error code.") from error
    except OSError as error:
        raise AssertionError(f"The {label} canary reached the operating system.") from error
    else:
        raise AssertionError(f"The Python guard allowed the {label} canary.")


def _assert_process_creation_guard() -> None:
    approved_argv = _approved_guarded_uvicorn_argv(
        "tests.backend.uvicorn_canary_app:app",
        43123,
    )
    approved_audit_arguments: tuple[object, ...] = (
        sys.executable,
        _LIST2CMDLINE(approved_argv),
        str(_REPO_ROOT),
        {},
    )
    if not _is_approved_guarded_uvicorn_child(approved_audit_arguments):
        raise AssertionError("The exact guarded Uvicorn child classifier rejected its canary.")
    rejected_command = list(approved_argv)
    rejected_command[6] = "pip"
    if _is_approved_guarded_uvicorn_child(
        (
            sys.executable,
            _LIST2CMDLINE(rejected_command),
            str(_REPO_ROOT),
            {},
        )
    ):
        raise AssertionError("The guarded child classifier accepted a different module.")
    approved_ruff_arguments: tuple[object, ...] = (
        None,
        _LIST2CMDLINE([str(_RUFF_EXECUTABLE), *_APPROVED_RUFF_ARGUMENTS[0]]),
        None,
        None,
    )
    if not _is_approved_ruff_child(approved_ruff_arguments):
        raise AssertionError("The exact Ruff validation child classifier rejected its canary.")
    changed_ruff_arguments = list(_APPROVED_RUFF_ARGUMENTS[0])
    changed_ruff_arguments[1] = "--fix"
    if _is_approved_ruff_child(
        (
            None,
            _LIST2CMDLINE([str(_RUFF_EXECUTABLE), *changed_ruff_arguments]),
            None,
            None,
        )
    ):
        raise AssertionError("The Ruff child classifier accepted a mutating command.")
    _assert_self_test_process_blocked(
        "changed Ruff subprocess",
        lambda: subprocess.run(
            [str(_RUFF_EXECUTABLE), *changed_ruff_arguments],
            check=False,
        ),
    )

    nonexistent = str(_REPO_ROOT / "var" / "tmp" / "phase-01-process-canary-missing.exe")
    _assert_self_test_process_blocked(
        "subprocess.Popen",
        lambda: subprocess.run(
            [nonexistent],
            executable=nonexistent,
            cwd=str(_REPO_ROOT),
            check=False,
        ),
    )
    _assert_self_test_process_blocked("os.system", lambda: os.system(""))
    _assert_self_test_process_blocked(
        "os.spawn",
        lambda: os.spawnv(os.P_WAIT, nonexistent, (nonexistent,)),
    )
    _assert_self_test_process_blocked(
        "os.exec",
        lambda: os.execv(nonexistent, (nonexistent,)),
    )
    if hasattr(os, "startfile"):
        _assert_self_test_process_blocked(
            "os.startfile",
            lambda: os.startfile(nonexistent),  # type: ignore[attr-defined]
        )


def _self_test() -> None:
    external_host = "phase-01-python-network-canary.example.invalid"
    _assert_self_test_blocked(
        "native external DNS",
        lambda: _socket.getaddrinfo(external_host, 443),
    )
    _assert_self_test_blocked(
        "native external getnameinfo",
        lambda: _socket.getnameinfo(("192.0.2.1", 443), 0),
    )
    _assert_self_test_blocked(
        "high-level external getnameinfo",
        lambda: socket.getnameinfo(("192.0.2.1", 443), 0),
    )
    _assert_process_creation_guard()

    override_calls: list[str] = []

    class ExternalStringAsLoopback(str):
        def __str__(self) -> str:
            override_calls.append("external-str.__str__")
            return "127.0.0.1"

        def strip(self, _characters: str | None = None) -> str:
            override_calls.append("external-str.strip")
            return "127.0.0.1"

        def lower(self) -> str:
            override_calls.append("external-str.lower")
            return "127.0.0.1"

    class ExternalBytesAsLoopback(bytes):
        def __bytes__(self) -> bytes:
            override_calls.append("external-bytes.__bytes__")
            return b"127.0.0.1"

        def decode(self, *_args: object, **_kwargs: object) -> str:
            override_calls.append("external-bytes.decode")
            return "127.0.0.1"

    class ExternalAddressAsLoopback(tuple):
        def __len__(self) -> int:
            override_calls.append("external-tuple.__len__")
            return 2

        def __iter__(self):
            override_calls.append("external-tuple.__iter__")
            return iter(("127.0.0.1", 443))

        def __getitem__(self, index: object) -> object:
            override_calls.append("external-tuple.__getitem__")
            return ("127.0.0.1", 443)[index]

    deceptive_external_addresses: tuple[tuple[str, object], ...] = (
        (
            "str-subclass external connect",
            (ExternalStringAsLoopback("192.0.2.1"), 443),
        ),
        (
            "bytes-subclass external connect",
            (ExternalBytesAsLoopback(b"192.0.2.1"), 443),
        ),
        (
            "tuple-subclass external connect",
            ExternalAddressAsLoopback(("192.0.2.1", 443)),
        ),
    )
    for native, socket_label in ((False, "high-level"), (True, "native")):
        socket_factory = _socket.socket if native else socket.socket
        for canary_label, address in deceptive_external_addresses:
            client = socket_factory(_socket.AF_INET, _socket.SOCK_STREAM)
            try:
                client.settimeout(0.01)
                _assert_self_test_blocked(
                    f"{socket_label} {canary_label}",
                    lambda client=client, address=address: client.connect(address),
                )
            finally:
                client.close()

    for resolver, resolver_label in (
        (socket.getaddrinfo, "high-level"),
        (_socket.getaddrinfo, "native"),
    ):
        for host, host_label in (
            (ExternalStringAsLoopback("192.0.2.1"), "str-subclass"),
            (ExternalBytesAsLoopback(b"192.0.2.1"), "bytes-subclass"),
        ):
            _assert_self_test_blocked(
                f"{resolver_label} {host_label} external DNS",
                lambda resolver=resolver, host=host: resolver(host, 443),
            )

    class LoopbackStringAsExternal(str):
        def __str__(self) -> str:
            override_calls.append("loopback-str.__str__")
            return "192.0.2.1"

        def strip(self, _characters: str | None = None) -> str:
            override_calls.append("loopback-str.strip")
            return "192.0.2.1"

        def lower(self) -> str:
            override_calls.append("loopback-str.lower")
            return "192.0.2.1"

    class LoopbackBytesAsExternal(bytes):
        def __bytes__(self) -> bytes:
            override_calls.append("loopback-bytes.__bytes__")
            return b"192.0.2.1"

        def decode(self, *_args: object, **_kwargs: object) -> str:
            override_calls.append("loopback-bytes.decode")
            return "192.0.2.1"

    class LoopbackAddressAsExternal(tuple):
        def __len__(self) -> int:
            override_calls.append("loopback-tuple.__len__")
            return 2

        def __iter__(self):
            override_calls.append("loopback-tuple.__iter__")
            return iter(("192.0.2.1", 443))

        def __getitem__(self, index: object) -> object:
            override_calls.append("loopback-tuple.__getitem__")
            return ("192.0.2.1", 443)[index]

    def assert_loopback_allowed(
        native: bool,
        address_factory: Callable[[int], object],
        label: str,
    ) -> None:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.settimeout(2)
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        port = server.getsockname()[1]
        received: list[bytes] = []

        def receive_once() -> None:
            connection, _ = server.accept()
            with connection:
                received.append(connection.recv(16))

        receiver = threading.Thread(target=receive_once, daemon=True)
        receiver.start()
        client_factory = _socket.socket if native else socket.socket
        client = client_factory(_socket.AF_INET, _socket.SOCK_STREAM)
        try:
            client.settimeout(2)
            client.connect(address_factory(port))
            client.sendall(b"loopback-ok")
        except OSError as error:
            raise AssertionError(f"The guard broke {label} loopback.") from error
        finally:
            client.close()
        receiver.join(timeout=2)
        server.close()
        if receiver.is_alive() or received != [b"loopback-ok"]:
            raise AssertionError(f"The guard broke {label} loopback delivery.")

    for native, socket_label in ((False, "high-level"), (True, "native")):
        assert_loopback_allowed(
            native,
            lambda port: LoopbackAddressAsExternal((LoopbackStringAsExternal("127.0.0.1"), port)),
            f"{socket_label} str/tuple-subclass",
        )
        assert_loopback_allowed(
            native,
            lambda port: (LoopbackBytesAsExternal(b"127.0.0.1"), port),
            f"{socket_label} bytes-subclass",
        )

    if override_calls:
        raise AssertionError(
            "The Python guard invoked an attacker-controlled address override: "
            + ", ".join(override_calls)
        )
    print("Python runtime offline network guard verified.")


def _parse_target(arguments: Sequence[str]) -> tuple[str, str, list[str]]:
    if len(arguments) < 2 or arguments[0] not in {"--module", "--script"}:
        raise ValueError(
            "Usage: python_runtime_guard.py (--module MODULE|--script SCRIPT) -- [ARGS...]"
        )
    target_kind = arguments[0][2:]
    target = arguments[1]
    if target_kind == "module":
        if not target or any(
            not (part.isidentifier() and not part.startswith("_")) for part in target.split(".")
        ):
            raise ValueError("The guarded Python module name is invalid.")
    else:
        if target != str(_SECRET_SCAN_DRIVER):
            raise ValueError("The guarded Python script is not the exact approved driver path.")
        try:
            script_status = os.lstat(target)
            resolved_target = Path(target).resolve(strict=True)
        except OSError as error:
            raise ValueError("The guarded Python script path is invalid.") from error
        file_attributes = getattr(script_status, "st_file_attributes", 0)
        reparse_attribute = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        if (
            resolved_target != _SECRET_SCAN_DRIVER
            or not stat.S_ISREG(script_status.st_mode)
            or script_status.st_nlink != 1
            or (reparse_attribute and file_attributes & reparse_attribute)
        ):
            raise ValueError("The guarded Python script is not a regular exact-path file.")
    remainder = list(arguments[2:])
    if not remainder or remainder[0] != "--":
        raise ValueError("The guarded Python module arguments require a -- separator.")
    return target_kind, target, remainder[1:]


def main() -> int:
    _install_guard()
    _activate_guarded_site()
    if sys.argv[1:] == ["--self-test"]:
        _self_test()
        return 0
    target_kind, target, arguments = _parse_target(sys.argv[1:])
    sys.argv = [target, *arguments]
    if target_kind == "module":
        runpy.run_module(target, run_name="__main__", alter_sys=True)
    else:
        runpy.run_path(target, run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
