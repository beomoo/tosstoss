import json
from pathlib import Path

from toss_dashboard_api.main import app

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_openapi_snapshot_matches_application() -> None:
    snapshot = json.loads((PROJECT_ROOT / "contracts" / "openapi.json").read_text(encoding="utf-8"))
    assert snapshot == app.openapi()


def test_phase_one_routes_are_read_only_and_exact() -> None:
    operations = {
        (method.upper(), path) for path, item in app.openapi()["paths"].items() for method in item
    }
    assert operations == {
        ("GET", "/health"),
        ("GET", "/api/v1/system/status"),
        ("GET", "/api/v1/securities"),
        ("GET", "/api/v1/companies/{issuer_id}/overview"),
        ("GET", "/api/v1/companies/{issuer_id}/data-quality"),
        ("GET", "/api/v1/sample/analysis-packet"),
    }
