import json

import pytest
from pydantic import ValidationError

from toss_dashboard_api.contracts.issuer import Issuer
from toss_dashboard_api.contracts.market import DailyMarketFlow


def test_null_requires_structured_missing_reason(fixture_repository) -> None:
    flow = next(item for item in fixture_repository.market_flows if item.net_value is None)
    payload = flow.model_dump(mode="json")
    payload["missing_reasons"] = {}
    with pytest.raises(ValidationError):
        DailyMarketFlow.model_validate_json(json.dumps(payload))


def test_non_null_rejects_stale_missing_reason(fixture_repository) -> None:
    flow = fixture_repository.market_flows[0]
    payload = flow.model_dump(mode="json")
    payload["missing_reasons"] = {"net_value": "UNAVAILABLE"}
    with pytest.raises(ValidationError):
        DailyMarketFlow.model_validate_json(json.dumps(payload))


def test_unknown_enum_is_rejected(fixture_repository) -> None:
    payload = fixture_repository.issuers[0].model_dump(mode="json")
    payload["jurisdiction"] = "XX"
    with pytest.raises(ValidationError):
        Issuer.model_validate_json(json.dumps(payload, ensure_ascii=False))
