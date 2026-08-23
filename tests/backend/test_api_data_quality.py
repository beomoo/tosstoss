def test_data_quality_preserves_independent_status_axes(api_client) -> None:
    response = api_client.get("/api/v1/companies/issuer_us_synthetic/data-quality")
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 2
    by_dataset = {item["dataset"]: item for item in payload["data"]}
    failed = by_dataset["SYNTHETIC_HOLDING"]
    assert failed["availability_status"] == "ERROR"
    assert failed["freshness_status"] == "STALE"
    assert failed["last_success_at"] == "2026-08-16T01:00:00Z"
    assert failed["source_locator"].startswith("fixture://")
    unavailable = by_dataset["SYNTHETIC_FINANCIAL"]
    assert unavailable["last_success_at"] is None
    assert unavailable["missing_reasons"]["last_success_at"] == "UNAVAILABLE"


def test_unknown_issuer_data_quality_returns_404(api_client) -> None:
    response = api_client.get("/api/v1/companies/issuer_missing/data-quality")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
