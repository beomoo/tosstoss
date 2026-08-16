import json
from decimal import Decimal

import pytest
from pydantic import ValidationError

from toss_dashboard_api.contracts.market import PriceBar


def test_json_number_decimal_is_rejected(fixture_repository) -> None:
    payload = fixture_repository.price_bars[0].model_dump(mode="json")
    payload["open"] = 100.25
    with pytest.raises(ValidationError):
        PriceBar.model_validate_json(json.dumps(payload))


def test_large_decimal_roundtrip_is_exact(fixture_repository) -> None:
    bar = next(
        item for item in fixture_repository.price_bars if item.price_bar_id == "price_kr_20260814"
    )
    assert bar.volume == Decimal("999999999999999999999999.000100")
    dumped = json.loads(bar.model_dump_json())
    assert dumped["volume"] == "999999999999999999999999.000100"


@pytest.mark.parametrize("invalid", ["1e3", "NaN", "Infinity", "01.0", "+1.0"])
def test_noncanonical_decimal_string_is_rejected(fixture_repository, invalid: str) -> None:
    payload = fixture_repository.price_bars[0].model_dump(mode="json")
    payload["open"] = invalid
    with pytest.raises(ValidationError):
        PriceBar.model_validate_json(json.dumps(payload))
