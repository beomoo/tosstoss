import json
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import Column, Integer, MetaData, Table, create_engine, select

from toss_dashboard_api.contracts.market import PriceBar
from toss_dashboard_api.storage.decimal_text import DecimalText


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


def test_large_decimal_json_sqlite_text_api_roundtrip_is_exact(
    fixture_repository, workspace_tmp_path: Path
) -> None:
    exact = "999999999999999999999999.000100"
    fixture_bar = next(
        item for item in fixture_repository.price_bars if item.price_bar_id == "price_kr_20260814"
    )
    fixture_json = fixture_bar.model_dump_json()
    parsed = PriceBar.model_validate_json(fixture_json)
    assert parsed.volume == Decimal(exact)

    engine = create_engine(f"sqlite:///{(workspace_tmp_path / 'decimal.sqlite3').as_posix()}")
    metadata = MetaData()
    values = Table(
        "decimal_roundtrip",
        metadata,
        Column("record_id", Integer, primary_key=True),
        Column("value", DecimalText(), nullable=False),
    )
    try:
        metadata.create_all(engine)
        with engine.begin() as connection:
            connection.execute(values.insert().values(record_id=1, value=parsed.volume))
            raw_value = connection.exec_driver_sql(
                "SELECT value FROM decimal_roundtrip WHERE record_id = 1"
            ).scalar_one()
            typed_value = connection.execute(
                select(values.c.value).where(values.c.record_id == 1)
            ).scalar_one()
        assert raw_value == exact
        assert typed_value == Decimal(exact)
    finally:
        engine.dispose()

    response_bar = parsed.model_copy(update={"volume": typed_value})
    application = FastAPI()

    def roundtrip_response() -> PriceBar:
        return response_bar

    application.add_api_route("/roundtrip", roundtrip_response, response_model=PriceBar)
    with TestClient(application) as client:
        response = client.get("/roundtrip")
    assert response.status_code == 200
    assert response.json()["volume"] == exact


@pytest.mark.parametrize("invalid", ["1e3", "NaN", "Infinity", "01.0", "+1.0"])
def test_noncanonical_decimal_string_is_rejected(fixture_repository, invalid: str) -> None:
    payload = fixture_repository.price_bars[0].model_dump(mode="json")
    payload["open"] = invalid
    with pytest.raises(ValidationError):
        PriceBar.model_validate_json(json.dumps(payload))
