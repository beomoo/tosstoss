import json
import shutil

import pytest
from fastapi.testclient import TestClient
from tests.backend.conftest import FIXTURE_DIR

from toss_dashboard_api.config import Settings
from toss_dashboard_api.main import create_app


def test_health_is_liveness_only(api_client) -> None:
    response = api_client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "toss-dashboard-api"
    assert payload["version"] == "0.1.0"
    assert payload["data_mode"] == "FIXTURE"
    assert payload["status"] == "ok"


def test_system_status_exposes_allowlisted_safety_state(api_client) -> None:
    response = api_client.get("/api/v1/system/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["database_revision"] == "0001_phase_01"
    assert payload["fixture_version"] == "0.1.0"
    assert payload["safety"] == {
        "contract_version": "0.1.0",
        "missing_reasons": {},
        "local_only": True,
        "trading_enabled": False,
        "dry_run": True,
        "openai_api_enabled": False,
        "allow_account_endpoints": False,
    }
    rendered = response.text.lower()
    assert "database_url" not in rendered
    assert "fixture_dir" not in rendered


def test_only_exact_local_cors_origin_is_allowed(api_client) -> None:
    allowed = api_client.options(
        "/api/v1/securities",
        headers={
            "origin": "http://127.0.0.1:3000",
            "access-control-request-method": "GET",
        },
    )
    assert allowed.headers["access-control-allow-origin"] == "http://127.0.0.1:3000"
    denied = api_client.options(
        "/api/v1/securities",
        headers={"origin": "https://example.invalid", "access-control-request-method": "GET"},
    )
    assert "access-control-allow-origin" not in denied.headers


def test_startup_rejects_same_version_with_different_manifest_digest(
    database_context, workspace_tmp_path
) -> None:
    fixture_dir = workspace_tmp_path / "different-manifest"
    shutil.copytree(FIXTURE_DIR, fixture_dir)
    manifest_path = fixture_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["generated_at"] = "2026-08-16T02:00:01Z"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    app = create_app(Settings(database_url=database_context.url, fixture_dir=fixture_dir))
    with pytest.raises(RuntimeError, match="manifest digest"):
        with TestClient(app):
            pass
