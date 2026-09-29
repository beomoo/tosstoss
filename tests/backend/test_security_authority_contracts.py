from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError
from tests.backend.security_authority_test_support import HASH, NOW, policy, record

from toss_dashboard_api.contracts import security_authority as c
from toss_dashboard_api.contracts.enums import Jurisdiction, MappingStatus, ShareClass


def test_canonical_vectors_and_audit_clock_exclusion() -> None:
    assert c.canonical_security_bytes({"z": None, "a": "e\u0301", "time": NOW}) == (
        '{"a":"é","time":"2026-09-29T01:02:03.000000Z","z":null}'.encode()
    )
    p = policy()
    fields = p.model_dump(exclude={"content_hash", "audit_hash", "recorded_at"})
    later = c.seal_security_record(c.SourcePolicy, **fields, recorded_at=NOW + timedelta(seconds=1))
    assert later.content_hash == p.content_hash
    assert later.audit_hash != p.audit_hash
    assert c.SourcePolicy.model_validate_json(c.canonical_security_bytes(p)) == p


@pytest.mark.parametrize(
    "value",
    [1.0, float("nan"), float("inf"), {1: "key"}, {"é": 1, "e\u0301": 2}, datetime(2026, 1, 1)],
)
def test_canonical_rejects_ambiguous_values(value) -> None:
    with pytest.raises(ValueError):
        c.canonical_security_bytes(value)


@pytest.mark.parametrize("raw", ['{"a":1,"a":2}', '{"é":1,"e\\u0301":2}', "1.5", "NaN", "Infinity"])
def test_json_rejects_duplicates_and_floats(raw: str) -> None:
    with pytest.raises(ValueError):
        c.strict_security_json(raw)


def test_anchors_and_closed_legacy_enums() -> None:
    anchor = c.kr_anchor("issuer_test", "KR7005930003")
    assert anchor == "security-v1|issuer_test|KRX_ISIN|KR7005930003"
    assert c.security_id_for_anchor(anchor).startswith("security_")
    identity = c.RegisteredClassIdentity(
        verified_registrant_cik="0000000001",
        accepted_accession="0000000002-26-000001",
        filing_document_digest=HASH,
        filing_form="8-A12B",
        registered_class_title="Class A Common",
        section_12_basis="12(b)",
        official_class_discriminator="Class A",
        registered_exchange_text="NASDAQ",
    )
    assert "/0000000002-26-000001/" in c.us_anchor("issuer_test", identity)
    other = identity.model_copy(
        update={
            "registered_class_title": "Class B Common",
            "official_class_discriminator": "Class B",
        }
    )
    assert c.us_anchor("issuer_test", other) != c.us_anchor("issuer_test", identity)
    assert list(ShareClass) == [ShareClass.COMMON]
    assert {v.value for v in MappingStatus} == {"VERIFIED", "UNRESOLVED"}
    assert {v.value for v in Jurisdiction} == {"KR", "US"}


@pytest.mark.parametrize(
    "isin", ["KR7005930004", "kr7005930003", "KR700593000", "KR7005930003/", "KR7005930003|"]
)
def test_invalid_isin_rejected(isin: str) -> None:
    with pytest.raises(ValueError):
        c.kr_anchor("issuer_test", isin)


@pytest.mark.parametrize("issuer", ["issuer/test", "issuer|test", "ISSUER_TEST"])
def test_anchor_delimiters_and_unapproved_case(issuer: str) -> None:
    with pytest.raises(ValueError):
        c.kr_anchor(issuer, "KR7005930003")


def test_contract_fields_and_hashes_are_closed() -> None:
    p = policy()
    data = p.model_dump()
    with pytest.raises(ValidationError):
        c.SourcePolicy.model_validate(data | {"ticker": "arbitrary"})
    with pytest.raises(ValidationError):
        c.SourcePolicy.model_validate(data | {"content_hash": HASH})
    with pytest.raises(ValidationError):
        c.SourcePolicy.model_validate(data | {"policy_version": "changed"})
    with pytest.raises(ValidationError):
        record(
            c.SourcePolicy,
            **p.model_dump(
                exclude={
                    "contract_version",
                    "content_hash",
                    "audit_hash",
                    "recorded_at",
                    "production_eligible",
                }
            ),
            production_eligible=1,
        )
