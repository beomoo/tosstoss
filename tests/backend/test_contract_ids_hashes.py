import pytest

from toss_dashboard_api.contracts.base import normalized_hash
from toss_dashboard_api.repositories.fixture import FixtureValidationError, _assert_no_cycles


def test_every_fixture_normalized_hash_matches(fixture_repository) -> None:
    groups = [
        fixture_repository.issuers,
        fixture_repository.securities,
        fixture_repository.source_records,
        fixture_repository.price_bars,
        fixture_repository.market_flows,
        fixture_repository.financial_facts,
        fixture_repository.institution_managers,
        fixture_repository.institution_holdings,
        fixture_repository.institution_holding_changes,
        fixture_repository.filing_documents,
        fixture_repository.filing_sentence_changes,
        fixture_repository.valuation_scenarios,
        fixture_repository.evidence,
        fixture_repository.data_quality_statuses,
    ]
    for records in groups:
        for record in records:
            assert normalized_hash(record) == record.normalized_content_hash
    assert (
        normalized_hash(fixture_repository.packet)
        == fixture_repository.packet.normalized_content_hash
    )


def test_revision_cycle_is_rejected() -> None:
    class Record:
        def __init__(self, record_id: str, parent_id: str) -> None:
            self.record_id = record_id
            self.parent_id = parent_id

    records = [Record("a", "b"), Record("b", "a")]
    with pytest.raises(FixtureValidationError, match="cycle"):
        _assert_no_cycles(records, "record_id", "parent_id")  # type: ignore[arg-type]


def test_manifest_and_raw_hashes_are_verified(fixture_repository) -> None:
    assert fixture_repository.manifest.fixture_version == "0.1.0"
    assert fixture_repository.manifest_digest.startswith("sha256:")
    assert len(fixture_repository.source_records) >= 3
