import json
from datetime import UTC

import pytest
from pydantic import ValidationError

from toss_dashboard_api.contracts.market import PriceBar


def test_offset_timestamp_normalizes_to_utc(fixture_repository) -> None:
    bar = next(
        item for item in fixture_repository.price_bars if item.price_bar_id == "price_kr_20260813"
    )
    assert bar.bar_start.tzinfo == UTC
    assert json.loads(bar.model_dump_json())["bar_start"] == "2026-08-12T15:00:00Z"


def test_naive_timestamp_is_rejected(fixture_repository) -> None:
    payload = fixture_repository.price_bars[0].model_dump(mode="json")
    payload["bar_start"] = "2026-08-14T00:00:00"
    with pytest.raises(ValidationError):
        PriceBar.model_validate_json(json.dumps(payload))


def test_trade_date_remains_date_only(fixture_repository) -> None:
    dumped = json.loads(fixture_repository.price_bars[0].model_dump_json())
    assert dumped["exchange_trade_date"] == "2026-08-13"
    assert "T" not in dumped["exchange_trade_date"]
