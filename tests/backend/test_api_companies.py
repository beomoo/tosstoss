def test_securities_returns_two_synthetic_records(api_client) -> None:
    response = api_client.get("/api/v1/securities")
    assert response.status_code == 200
    payload = response.json()
    assert payload["data_mode"] == "FIXTURE"
    assert payload["count"] == 2
    assert {item["ticker"] for item in payload["data"]} == {"KRFIX1", "USFXZZ"}


def test_company_overview_is_fixture_aggregate(api_client) -> None:
    response = api_client.get("/api/v1/companies/issuer_kr_synthetic/overview")
    assert response.status_code == 200
    payload = response.json()
    assert payload["data_mode"] == "FIXTURE"
    assert payload["data"]["selected_security_id"] == "security_kr_synthetic_common"
    assert payload["data"]["issuer"]["display_name"] == "새봄전력 (합성)"
    assert payload["data"]["financial_facts"][1]["value"] is None
    assert payload["data"]["valuation_scenarios"][0]["result_status"] == "SAMPLE_RESULT"


def test_unknown_company_returns_safe_404(api_client) -> None:
    response = api_client.get("/api/v1/companies/issuer_missing/overview")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
    assert "traceback" not in response.text.lower()
