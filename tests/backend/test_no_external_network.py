import ast
import socket
from pathlib import Path

import pytest
from pytest_socket import SocketConnectBlockedError

from toss_dashboard_api.repositories.fixture import FixtureRepository

PROJECT_ROOT = Path(__file__).resolve().parents[2]
API_ROOT = PROJECT_ROOT / "services" / "api" / "src" / "toss_dashboard_api"


def test_backend_has_no_external_http_client_imports() -> None:
    prohibited = {"requests", "httpx", "aiohttp", "urllib3", "openai"}
    violations: list[str] = []
    for path in API_ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name.split(".")[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module.split(".")[0]]
            if prohibited.intersection(names):
                violations.append(str(path.relative_to(PROJECT_ROOT)))
    assert violations == []


def test_no_connector_or_account_route_exists() -> None:
    assert not (API_ROOT / "connectors").exists()
    route_names = {path.name for path in (API_ROOT / "routes").glob("*.py")}
    assert "account.py" not in route_names
    assert "orders.py" not in route_names


def test_fixture_loading_does_not_open_a_network_connection(
    socket_disabled: None,
) -> None:
    FixtureRepository(PROJECT_ROOT / "fixtures" / "phase_01")


def test_pytest_socket_blocks_non_loopback_connections() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as outbound:
        with pytest.raises(SocketConnectBlockedError):
            outbound.connect(("192.0.2.1", 9))
