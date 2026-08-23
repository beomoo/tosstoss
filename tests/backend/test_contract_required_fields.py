import json

import pytest
from pydantic import ValidationError

from toss_dashboard_api.contracts.issuer import Issuer
from toss_dashboard_api.contracts.market import PriceBar


def test_contract_version_is_required(fixture_repository) -> None:
    payload = fixture_repository.price_bars[0].model_dump(mode="json")
    del payload["contract_version"]
    with pytest.raises(ValidationError):
        PriceBar.model_validate_json(json.dumps(payload))


def test_stable_id_is_required(fixture_repository) -> None:
    payload = fixture_repository.issuers[0].model_dump(mode="json")
    del payload["issuer_id"]
    with pytest.raises(ValidationError):
        Issuer.model_validate_json(json.dumps(payload, ensure_ascii=False))


def test_unknown_contract_version_is_rejected(fixture_repository) -> None:
    payload = fixture_repository.issuers[0].model_dump(mode="json")
    payload["contract_version"] = "0.2.0"
    with pytest.raises(ValidationError):
        Issuer.model_validate_json(json.dumps(payload, ensure_ascii=False))
