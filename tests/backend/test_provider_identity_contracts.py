from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from toss_dashboard_api.contracts.base import sha256_prefixed
from toss_dashboard_api.contracts.enums import (
    MappingStatus,
    Market,
    ProviderDataset,
    ProviderIdentifierKind,
    ProviderIdentifierReason,
    ProviderIdentityState,
    ProviderSystem,
)
from toss_dashboard_api.contracts.provider_identity import (
    PROVIDER_IDENTITY_CONTRACT_VERSION,
    ProviderIdentifierHistory,
    ProviderIdentityMapping,
    ProviderLatestPointer,
    ProviderSecurityIdentity,
    provider_latest_pointer_id,
)


def identity_payload() -> dict[str, object]:
    digest = "1" * 64
    return {
        "provider_security_identity_id": f"tpsi_{digest}",
        "provider": ProviderSystem.TOSS_OPEN_API,
        "market": Market.KR,
        "allocation_anchor_hash": f"sha256:{digest}",
        "identity_state": ProviderIdentityState.ACTIVE,
        "mapping_status": MappingStatus.UNRESOLVED,
        "first_source_version_id": "tsrc_first",
        "latest_source_version_id": "tsrc_first",
        "provider_contract_version": PROVIDER_IDENTITY_CONTRACT_VERSION,
    }


def test_provider_identity_contract_is_extra_forbid() -> None:
    payload = identity_payload()
    payload["corp_code"] = "must-not-exist"
    with pytest.raises(ValidationError, match="corp_code"):
        ProviderSecurityIdentity.model_validate(payload)


def test_provider_identity_contract_version_is_local_and_exact() -> None:
    payload = identity_payload()
    payload["provider_contract_version"] = "toss-identity/0.1.1"
    with pytest.raises(ValidationError, match="provider_contract_version"):
        ProviderSecurityIdentity.model_validate(payload)


def test_provider_identity_id_must_match_immutable_anchor_hash() -> None:
    payload = identity_payload()
    payload["provider_security_identity_id"] = "tpsi_" + "2" * 64
    with pytest.raises(ValidationError, match="immutable anchor"):
        ProviderSecurityIdentity.model_validate(payload)


def test_identity_foundation_cannot_self_promote_to_verified() -> None:
    payload = identity_payload()
    payload["mapping_status"] = MappingStatus.VERIFIED
    with pytest.raises(ValidationError, match="self-promote"):
        ProviderSecurityIdentity.model_validate(payload)


def test_identifier_history_rejects_inverted_validity() -> None:
    with pytest.raises(ValidationError, match="valid_from"):
        ProviderIdentifierHistory(
            identifier_history_id="pih_invalid_range",
            provider_security_identity_id="tpsi_" + "1" * 64,
            identifier_kind=ProviderIdentifierKind.SYMBOL,
            identifier_value="A",
            valid_from=date(2026, 8, 26),
            valid_to=date(2026, 8, 25),
            source_version_id="tsrc_first",
            revision_reason=ProviderIdentifierReason.INITIAL,
            provider_contract_version=PROVIDER_IDENTITY_CONTRACT_VERSION,
        )


def test_unresolved_mapping_rejects_canonical_linkage() -> None:
    with pytest.raises(ValidationError, match="unresolved mapping"):
        ProviderIdentityMapping(
            mapping_id="pmap_invalid_unresolved",
            provider_security_identity_id="tpsi_" + "1" * 64,
            issuer_id="issuer_kr_synthetic",
            security_id="security_kr_synthetic_common",
            mapping_status=MappingStatus.UNRESOLVED,
            evidence_source_version_id="tsrc_first",
            approved_at=datetime(2026, 8, 25, tzinfo=UTC),
            valid_from=None,
            valid_to=None,
            provider_contract_version=PROVIDER_IDENTITY_CONTRACT_VERSION,
        )


def test_latest_pointer_identity_is_dataset_and_provider_scoped() -> None:
    identity_id = "tpsi_" + "1" * 64
    expected = provider_latest_pointer_id(ProviderDataset.STOCK_DETAIL, identity_id)
    pointer = ProviderLatestPointer(
        latest_pointer_id=expected,
        dataset=ProviderDataset.STOCK_DETAIL,
        provider_security_identity_id=identity_id,
        normalized_record_id="normalized_stock_a",
        source_version_id="tsrc_first",
        accepted_observed_at=None,
        accepted_observed_date=None,
        state_hash=sha256_prefixed(b"state"),
        provider_contract_version=PROVIDER_IDENTITY_CONTRACT_VERSION,
    )
    assert pointer.latest_pointer_id == expected
    with pytest.raises(ValidationError, match="dataset and provider identity"):
        ProviderLatestPointer.model_validate(
            {**pointer.model_dump(), "latest_pointer_id": "tlatest_" + "0" * 64}
        )
