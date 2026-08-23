import ast
import socket
from pathlib import Path

import pytest
from pytest_socket import SocketConnectBlockedError

from toss_dashboard_api.connectors.toss import auth as toss_auth
from toss_dashboard_api.connectors.toss.client import TossHttpClient
from toss_dashboard_api.repositories.fixture import FixtureRepository

PROJECT_ROOT = Path(__file__).resolve().parents[2]
API_ROOT = PROJECT_ROOT / "services" / "api" / "src" / "toss_dashboard_api"
CONNECTOR_ROOT = API_ROOT / "connectors"
TOSS_CONNECTOR_ROOT = CONNECTOR_ROOT / "toss"


def test_backend_external_http_client_imports_are_confined_to_toss_connector() -> None:
    prohibited_everywhere = {"requests", "aiohttp", "urllib3", "openai"}
    violations: list[str] = []
    for path in API_ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name.split(".")[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module.split(".")[0]]
            has_prohibited_import = bool(prohibited_everywhere.intersection(names))
            has_misplaced_httpx = "httpx" in names and not path.is_relative_to(TOSS_CONNECTOR_ROOT)
            if has_prohibited_import or has_misplaced_httpx:
                violations.append(str(path.relative_to(PROJECT_ROOT)))
    assert violations == []


def test_only_exact_cp2_d1_toss_connector_files_are_present() -> None:
    connector_files = {
        path.relative_to(CONNECTOR_ROOT).as_posix()
        for path in CONNECTOR_ROOT.rglob("*")
        if path.is_file() and path.suffix == ".py"
    }
    connector_directories = {
        path.relative_to(CONNECTOR_ROOT).as_posix()
        for path in CONNECTOR_ROOT.rglob("*")
        if path.is_dir() and path.name != "__pycache__"
    }
    assert connector_directories == {"toss"}
    assert connector_files == {
        "__init__.py",
        "toss/__init__.py",
        "toss/auth.py",
        "toss/client.py",
        "toss/errors.py",
        "toss/models.py",
        "toss/preflight.py",
        "toss/rate_limit.py",
    }


def test_no_account_or_order_route_exists() -> None:
    route_names = {path.name for path in (API_ROOT / "routes").glob("*.py")}
    assert "account.py" not in route_names
    assert "orders.py" not in route_names


def test_application_runtime_has_no_token_manager_or_raw_token_surface() -> None:
    assert "token_manager" not in vars(TossHttpClient)
    assert "TokenLease" not in vars(toss_auth)
    assert "TossTokenManager" not in vars(toss_auth)
    runtime_types = [value for value in vars(toss_auth).values() if isinstance(value, type)]
    assert all("_authorization_value" not in vars(runtime_type) for runtime_type in runtime_types)


def test_fixture_loading_does_not_open_a_network_connection(
    socket_disabled: None,
) -> None:
    FixtureRepository(PROJECT_ROOT / "fixtures" / "phase_01")


def test_pytest_socket_blocks_non_loopback_connections() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as outbound:
        with pytest.raises(SocketConnectBlockedError):
            outbound.connect(("192.0.2.1", 9))
