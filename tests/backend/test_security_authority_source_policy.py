from __future__ import annotations

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from tests.backend.security_authority_test_support import (
    approved_issuer,
    candidate,
    insert,
    policy,
    record,
)

from toss_dashboard_api.contracts import security_authority as c
from toss_dashboard_api.repositories.security_authority import (
    SecurityLedgerConflict,
    SQLiteSecurityAuthorityRepository,
)
from toss_dashboard_api.storage.database import session_factory


def production_policy(**changes) -> c.SourcePolicy:
    fields = policy().model_dump(
        exclude={"contract_version", "recorded_at", "content_hash", "audit_hash"}
    )
    fields.update(
        source_namespace="SEC_ACCEPTED_8A",
        document_kind="SEC_ACCEPTED_8A",
        authority_classification="OFFICIAL_AUTHORITY",
        ingestion_mode="AUTOMATED_OFFICIAL_PUBLIC",
        production_eligible=1,
        access_disposition="PERMITTED",
        license_disposition="PERMITTED",
        origin_mode="PRODUCTION_AUTHORITY",
        fixture_taint=0,
        test_taint=0,
        max_weight=3,
        credential_free_locator_root="https://www.sec.gov/Archives/edgar/data/",
    )
    return record(c.SourcePolicy, **(fields | changes))


@pytest.mark.parametrize(
    "locator",
    [
        "",
        "*",
        "?",
        "fixture://security/",
        "http://not-https",
        "ftp://authority/",
        "https://",
        "authority-verification://",
        "HTTPS://www.sec.gov/",
        "https://*/",
        "https://www.sec.gov/*",
        "https://www.sec.gov/?",
        "https://www.sec.gov/[A-Z]/",
        "https://www.sec.gov/{record}/",
        "https://www.sec.gov/%2A/",
        "https://www.sec.gov/#fragment",
        "https://user:<synthetic-placeholder>@www.sec.gov/",
        "https://www.sec.gov/white space/",
        "https://www.sec.gov/\n",
        "https://www.sec.gov/\x00",
        "https://www.sec.gov/" + "a" * 2048,
    ],
)
def test_production_locator_rejected_by_contract_and_raw_sql(database_context, locator) -> None:
    with pytest.raises(ValidationError):
        production_policy(credential_free_locator_root=locator)
    with database_context.engine.begin() as connection:
        with pytest.raises(IntegrityError, match="CHECK constraint failed"):
            insert(connection, production_policy(), credential_free_locator_root=locator)


@pytest.mark.parametrize(
    "locator",
    ["https://www.sec.gov/Archives/edgar/data/", "authority-verification://kr-supreme-court/"],
)
def test_existing_b_locator_schemes_are_representable_but_not_admitted(
    database_context, locator
) -> None:
    # These are frozen B registry roots, not new Security source access approvals.
    value = production_policy(credential_free_locator_root=locator)
    with database_context.engine.begin() as connection:
        insert(connection, value)
        assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []
    repository = SQLiteSecurityAuthorityRepository(session_factory(database_context.engine))
    with pytest.raises(
        SecurityLedgerConflict, match="SECURITY_PRODUCTION_ADMISSION_NOT_IMPLEMENTED"
    ):
        repository.insert_or_verify(value)


def test_isolated_fixture_locator_is_accepted(database_context) -> None:
    value = policy()
    assert value.production_eligible == 0
    with database_context.engine.begin() as connection:
        insert(connection, value)
        assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []


@pytest.mark.parametrize(
    "changes",
    [
        {"fixture_taint": 1},
        {"test_taint": 1},
        {"source_namespace": "CGS"},
    ],
)
def test_tainted_or_cgs_production_policy_rejected_in_both_layers(
    database_context, changes
) -> None:
    with pytest.raises(ValidationError):
        production_policy(**changes)
    with database_context.engine.begin() as connection:
        with pytest.raises(IntegrityError, match="CHECK constraint failed"):
            insert(connection, production_policy(), **changes)


@pytest.mark.parametrize(
    "changes",
    [
        {"origin_mode": "PRODUCTION_AUTHORITY"},
        {"ingestion_mode": "AUTOMATED_OFFICIAL_PUBLIC"},
        {"fixture_taint": 0, "test_taint": 0},
    ],
)
def test_fixture_locator_requires_isolated_tainted_policy(database_context, changes) -> None:
    value = policy()
    fields = value.model_dump(
        exclude={"contract_version", "recorded_at", "content_hash", "audit_hash"}
    )
    with pytest.raises(ValidationError):
        record(c.SourcePolicy, **(fields | changes))
    with database_context.engine.begin() as connection:
        with pytest.raises(IntegrityError, match="CHECK constraint failed"):
            insert(connection, value, **changes)


@pytest.mark.parametrize("field", ["source_namespace", "document_kind"])
@pytest.mark.parametrize(
    "token", ["lowercase", "Mixed", "A-B", "A.B", "1TOKEN", "_TOKEN", "", "A" * 129, "A\n", "A\x00"]
)
def test_invalid_source_tokens_rejected_in_both_layers(database_context, field, token) -> None:
    with pytest.raises(ValidationError):
        production_policy(**{field: token})
    with database_context.engine.begin() as connection:
        with pytest.raises(IntegrityError, match="CHECK constraint failed"):
            insert(connection, production_policy(), **{field: token})


@pytest.mark.parametrize("field", ["source_namespace", "document_kind"])
@pytest.mark.parametrize("token", ["A", "A" * 128, "SEC_ACCEPTED_8A"])
def test_valid_source_token_boundaries_persist(database_context, field, token) -> None:
    value = production_policy(**{field: token})
    with database_context.engine.begin() as connection:
        insert(connection, value)
        assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []


@pytest.mark.parametrize("kind", ["evidence", "application"])
@pytest.mark.parametrize("field", ["source_namespace", "document_kind"])
def test_source_token_parity_also_covers_evidence_and_applications(
    database_context, kind, field
) -> None:
    issuer = approved_issuer(database_context)
    with database_context.engine.begin() as connection:
        values = candidate(connection, issuer)
        value = values[kind]
        fields = value.model_dump(
            exclude={"contract_version", "recorded_at", "content_hash", "audit_hash"}
        )
        with pytest.raises(ValidationError):
            record(type(value), **(fields | {field: "lowercase"}))
        with pytest.raises(IntegrityError, match="CHECK constraint failed"):
            insert(connection, value, **{field: "lowercase"})
