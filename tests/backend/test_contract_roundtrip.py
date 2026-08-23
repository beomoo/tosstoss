import json

from toss_dashboard_api.contracts.market import PriceBar


def test_json_model_json_roundtrip_is_stable(fixture_repository) -> None:
    original = fixture_repository.price_bars[1]
    restored = PriceBar.model_validate_json(original.model_dump_json())
    assert restored.model_dump(mode="json") == original.model_dump(mode="json")


def test_all_api_facing_fixture_records_are_serializable(fixture_repository) -> None:
    overview = fixture_repository.company_overview("issuer_kr_synthetic")
    assert overview is not None
    payload = json.loads(overview.model_dump_json())
    assert payload["issuer"]["display_name"] == "새봄전력 (합성)"
    assert payload["financial_facts"][1]["value"] is None
