"""C2 machine Security decisions over deterministic production-contract fixtures."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from threading import Barrier
from typing import Any

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from tests.backend.reviewer_test_support import Authenticator, Clock
from tests.backend.security_authority_test_support import HASH, insert, record
from tests.backend.test_authority_decision_engine import (
    EVALUATED_AT,
    KR_CORP_CODE,
    KR_SYMBOL,
    US_CIK,
    US_SYMBOL,
    _kr_harness,
    _kr_request,
    _us_harness,
    _us_request,
)
from tests.backend.test_reviewer_runtime import OWNER, enroll

from toss_dashboard_api.contracts import security_authority as c
from toss_dashboard_api.contracts.security_authority_decision import (
    KrxIssueBasicFact,
    KrxListingLifecycleFact,
    KrxStandardCodeFact,
    NasdaqPrimaryFact,
    OpenDartCorpCodeFact,
    SecAccepted8AFact,
    SecAccepted25Fact,
    SecurityAuthorityEvaluationRequest,
)
from toss_dashboard_api.domain.security_authority import SecurityAuthorityDecisionEngine
from toss_dashboard_api.domain.security_authority_registry import (
    SOURCE_POLICY_SPECS,
    exact_policy_for,
)
from toss_dashboard_api.reviewer.issuer_disposition import IssuerDispositionService
from toss_dashboard_api.reviewer.runtime import _Runtime
from toss_dashboard_api.storage.database import session_factory
from toss_dashboard_api.storage.models import ProviderIdentityMappingRow
from toss_dashboard_api.storage.security_authority_models import (
    SecurityApprovalChallengeRow,
    SecurityApprovalEventRow,
    SecurityAuthenticationEventRow,
    SecurityAuthorityLinkHeadRow,
    SecurityAuthorityLinkRow,
    SecurityAuthorityProfileRow,
    SecurityBundleProviderObservationRow,
    SecurityCanonicalSubjectRow,
    SecurityChallengeConsumptionRow,
    SecurityDecisionRow,
    SecuritySupersessionPairRow,
)

KR_ISIN = "KR7005930003"
SEC_ACCESSION = "0000789019-26-000001"
OLD_KR_ISIN = "KR7000660001"


def _source_subject(namespace: str, fact: Any) -> str:
    if namespace in ("KRX_STANDARD_CODE", "KRX_ISSUE_BASIC", "KRX_LISTING_LIFECYCLE"):
        return f"KRX_ISSUE:{fact.stock_code}"
    if namespace == "OPENDART_CORP_CODE":
        return f"OPENDART_ISSUER:{fact.corp_code}"
    if namespace == "SEC_ACCEPTED_8A":
        return "SEC_8A:" + c.security_hash(
            (
                fact.registrant_cik,
                fact.registered_class_title,
                fact.section_12_basis,
                fact.official_class_discriminator,
                fact.exchange_name,
            )
        )
    if namespace == "SEC_ACCEPTED_25":
        return "SEC_25:" + c.security_hash(
            (fact.registrant_cik, fact.class_description, fact.exchange_name)
        )
    if namespace == "SEC_PERIODIC_COVER":
        return "SEC_PERIODIC:" + c.security_hash((fact.registrant_cik, fact.class_title))
    if namespace == "NASDAQ_PRIMARY":
        return f"NASDAQ_ISSUE:{fact.symbol}"
    raise AssertionError(f"unhandled test fact namespace: {namespace}")


def _approve_issuer(
    context: Any,
    harness: Any,
    request: Any,
    *,
    authenticator: Authenticator | None = None,
    assertion_count: int = 9,
) -> Authenticator:
    ready = harness.engine.evaluate(request)
    assert ready.decision is not None
    runtime = _Runtime(
        context.engine,
        lambda: OWNER,
        Clock(EVALUATED_AT + timedelta(minutes=1)),
    )
    if authenticator is None:
        authenticator = Authenticator()
        enroll(runtime, authenticator, registration_count=7, assertion_count=8)
    service = IssuerDispositionService(runtime, harness.engine)
    challenge = service.issue(ready.decision.issuer_decision_id, "APPROVED")
    service.complete(
        challenge.challenge_id,
        authenticator.assertion(challenge.options, assertion_count),
        structured_reason_code="VERIFIED_EXACT_AUTHORITY",
        review_note="Synthetic B issuer prerequisite for C2 test",
    )
    return authenticator


def _source_fact(
    context: Any,
    namespace: str,
    role: c.SubjectRole,
    fact: Any,
    *,
    retrieved_at: datetime = EVALUATED_AT,
    source_as_of: datetime | None = None,
    effective_date: date | None = None,
    origin_mode: str = "PRODUCTION_AUTHORITY",
    fixture_taint: int = 0,
    test_taint: int = 0,
    exact_subject: str | None = None,
) -> c.Evidence:
    document_kinds = {
        "KRX_STANDARD_CODE": "KRX_STANDARD_CODE_RECORD",
        "KRX_ISSUE_BASIC": "KRX_ISSUE_BASIC_RECORD",
        "KRX_LISTING_LIFECYCLE": "KRX_LISTING_LIFECYCLE_RECORD",
        "OPENDART_CORP_CODE": "OPENDART_CORP_CODE_RECORD",
        "SEC_ACCEPTED_8A": "SEC_FORM_8A",
        "SEC_ACCEPTED_25": "SEC_FORM_25",
        "SEC_PERIODIC_COVER": "SEC_PERIODIC_COVER",
        "NASDAQ_PRIMARY": "NASDAQ_SYMBOL_DIRECTORY",
    }
    fact_bytes = c.canonical_security_bytes(fact)
    suffix = c.security_hash((namespace, fact_bytes.hex()))[7:]
    evidence = record(
        c.Evidence,
        evidence_id=f"evidence_c2_{suffix}",
        source_namespace=namespace,
        document_kind=document_kinds[namespace],
        accepted_document_identity=f"{namespace.lower()}-test-document-{suffix}",
        raw_digest=HASH,
        subject_role=role,
        exact_subject=exact_subject or _source_subject(namespace, fact),
        fact_key="NORMALIZED_SOURCE_FACT",
        fact_value=fact_bytes.decode("utf-8"),
        origin_mode=origin_mode,
        fixture_taint=fixture_taint,
        test_taint=test_taint,
        effective_date=effective_date,
        effective_date_missing_reason=(
            None if effective_date is not None else "NOT_SUPPLIED_BY_AUTHORITY"
        ),
    )
    observation = record(
        c.EvidenceObservation,
        observation_id=f"observation_c2_{suffix}",
        evidence_id=evidence.evidence_id,
        evidence_hash=evidence.content_hash,
        adapter_version="c2-normalized-stored-facts/1",
        parser_version="c2-normalized-stored-facts/1",
        run_id="c2_test_run",
        retrieved_at=retrieved_at,
        source_as_of=source_as_of,
        source_as_of_missing_reason=(
            None if source_as_of is not None else "NOT_SUPPLIED_BY_AUTHORITY"
        ),
        access_result="SUCCEEDED",
        raw_digest=HASH,
    )
    with context.engine.begin() as connection:
        insert(connection, evidence)
        insert(connection, observation)
    return evidence


def _relate_evidence(
    context: Any,
    prior: c.Evidence,
    successor: c.Evidence,
    *,
    relation_kind: str = "CORRECTS",
) -> None:
    relation = record(
        c.EvidenceRelation,
        relation_id="relation_c2_"
        + c.security_hash((prior.evidence_id, successor.evidence_id))[7:],
        prior_evidence_id=prior.evidence_id,
        prior_evidence_hash=prior.content_hash,
        successor_evidence_id=successor.evidence_id,
        successor_evidence_hash=successor.content_hash,
        relation_kind=relation_kind,
        effective_date=None,
        effective_date_missing_reason="NOT_SUPPLIED_BY_AUTHORITY",
    )
    with context.engine.begin() as connection:
        insert(connection, relation)


def _kr_base_facts(
    context: Any,
    *,
    issue_stock_code: str = KR_SYMBOL,
    issue_isin: str | None = KR_ISIN,
    stock_kind: str = "COMMON_EQUITY",
    listing_status: str = "ACTIVE",
    listing_date: date = date(1975, 6, 11),
    delisting_date: date | None = None,
    dart_stock_code: str = KR_SYMBOL,
    dart_corp_code: str = KR_CORP_CODE,
    standard_isin: str = KR_ISIN,
    standard_source_as_of: datetime | None = EVALUATED_AT - timedelta(hours=1),
    issue_source_as_of: datetime | None = EVALUATED_AT - timedelta(hours=1),
    listing_retrieved_at: datetime = EVALUATED_AT,
    dart_retrieved_at: datetime = EVALUATED_AT,
    include_standard: bool = True,
    include_issue: bool = True,
    include_listing: bool = True,
    include_dart: bool = True,
) -> c.Evidence | None:
    standard = (
        _source_fact(
            context,
            "KRX_STANDARD_CODE",
            c.SubjectRole.KRX_ISSUE,
            KrxStandardCodeFact(stock_code=KR_SYMBOL, isin=standard_isin),
            source_as_of=standard_source_as_of,
        )
        if include_standard
        else None
    )
    if include_issue:
        _source_fact(
            context,
            "KRX_ISSUE_BASIC",
            c.SubjectRole.KRX_ISSUE,
            KrxIssueBasicFact(
                stock_code=issue_stock_code,
                isin=issue_isin,
                market="KOSPI",
                ticker=KR_SYMBOL,
                security_type="STOCK",
                stock_kind=stock_kind,
                listing_date=listing_date,
                nationality="KR",
            ),
            source_as_of=issue_source_as_of,
            effective_date=listing_date,
        )
    if include_listing:
        _source_fact(
            context,
            "KRX_LISTING_LIFECYCLE",
            c.SubjectRole.KRX_ISSUE,
            KrxListingLifecycleFact(
                stock_code=KR_SYMBOL,
                market="KOSPI",
                ticker=KR_SYMBOL,
                security_type="STOCK",
                stock_kind=stock_kind,
                listing_date=listing_date,
                delisting_date=delisting_date,
                delisting_reason=("TEST DELISTING" if delisting_date is not None else None),
                nationality="KR",
                status=listing_status,
            ),
            retrieved_at=listing_retrieved_at,
            effective_date=delisting_date or listing_date,
        )
    if include_dart:
        _source_fact(
            context,
            "OPENDART_CORP_CODE",
            c.SubjectRole.DART_ISSUER,
            OpenDartCorpCodeFact(
                corp_code=dart_corp_code,
                formal_name="Synthetic Korean Corporation",
                stock_code=dart_stock_code,
                modify_date=EVALUATED_AT.date(),
            ),
            retrieved_at=dart_retrieved_at,
        )
    return standard


def _kr_evaluation(context: Any, **fact_options: Any):
    harness = _kr_harness(context, provider_isin=KR_ISIN)
    _approve_issuer(context, harness, _kr_request(harness))
    _kr_base_facts(context, **fact_options)
    engine = SecurityAuthorityDecisionEngine(
        session_factory(context.engine), clock=lambda: EVALUATED_AT
    )
    return (
        harness,
        engine,
        engine.evaluate(SecurityAuthorityEvaluationRequest(provider_id=harness.provider_id)),
    )


def _us_base_facts(
    context: Any,
    *,
    registered_cik: str = US_CIK,
    registered_class_title: str = "Common Stock",
    exchange_name: str = "NASDAQ",
    exchange_symbol: str = US_SYMBOL,
    sec_source_as_of: datetime | None = EVALUATED_AT - timedelta(hours=1),
    nasdaq_file_time: datetime = EVALUATED_AT - timedelta(hours=1),
    nasdaq_state: str = "ACTIVE",
    test_issue: bool = False,
    form25: bool = False,
    include_sec: bool = True,
    include_nasdaq: bool = True,
    accepted_accession: str = SEC_ACCESSION,
    nasdaq_security_name: str | None = None,
) -> None:
    if include_sec:
        _source_fact(
            context,
            "SEC_ACCEPTED_8A",
            c.SubjectRole.SEC_REGISTRANT,
            SecAccepted8AFact(
                registrant_cik=registered_cik,
                accepted_accession=accepted_accession,
                accepted_at=EVALUATED_AT - timedelta(days=2),
                filing_document_digest=HASH,
                registered_class_title=registered_class_title,
                section_12_basis="12(b)",
                official_class_discriminator="class-1",
                exchange_name=exchange_name,
            ),
            source_as_of=sec_source_as_of,
            effective_date=(EVALUATED_AT - timedelta(days=2)).date(),
        )
    if include_nasdaq:
        _source_fact(
            context,
            "NASDAQ_PRIMARY",
            c.SubjectRole.EXCHANGE_ISSUE,
            NasdaqPrimaryFact(
                symbol=exchange_symbol,
                security_name=nasdaq_security_name or registered_class_title,
                market_category="N",
                test_issue=test_issue,
                financial_status=None,
                file_creation_time=nasdaq_file_time,
                listing_date=date(1986, 3, 13),
                state=nasdaq_state,
            ),
            effective_date=date(1986, 3, 13),
        )
    if form25:
        _source_fact(
            context,
            "SEC_ACCEPTED_25",
            c.SubjectRole.EXCHANGE_ISSUE,
            SecAccepted25Fact(
                registrant_cik=US_CIK,
                accepted_accession="0000789019-26-000002",
                accepted_at=EVALUATED_AT - timedelta(hours=2),
                exchange_name="NASDAQ",
                class_description=registered_class_title,
                effective_date=EVALUATED_AT.date() - timedelta(days=1),
                event_kind="REMOVAL",
            ),
            effective_date=EVALUATED_AT.date() - timedelta(days=1),
        )


def _us_evaluation(context: Any, **fact_options: Any):
    harness = _us_harness(context)
    _approve_issuer(context, harness, _us_request(harness))
    _us_base_facts(context, **fact_options)
    engine = SecurityAuthorityDecisionEngine(
        session_factory(context.engine), clock=lambda: EVALUATED_AT
    )
    return (
        harness,
        engine,
        engine.evaluate(SecurityAuthorityEvaluationRequest(provider_id=harness.provider_id)),
    )


def test_kr_complete_source_graph_reaches_ready_without_c3_or_legacy_writes(
    database_context,
) -> None:
    _, _, result = _kr_evaluation(database_context)
    assert result.machine_state == "READY_FOR_MANUAL_REVIEW"
    assert result.decision is not None
    assert result.bundle is not None
    assert result.bundle.proposed_anchor.endswith(f"KRX_ISIN|{KR_ISIN}")
    assert result.collision.result == "CLEAR"
    assert {item.result for item in result.scope_results} == {"SATISFIED"}
    with session_factory(database_context.engine)() as session:
        for row_type in (
            SecurityApprovalChallengeRow,
            SecurityChallengeConsumptionRow,
            SecurityAuthenticationEventRow,
            SecurityApprovalEventRow,
            SecuritySupersessionPairRow,
            SecurityCanonicalSubjectRow,
            SecurityAuthorityProfileRow,
            SecurityAuthorityLinkRow,
            SecurityAuthorityLinkHeadRow,
        ):
            assert session.scalar(select(func.count()).select_from(row_type)) == 0
        assert (
            session.scalar(
                select(func.count())
                .select_from(ProviderIdentityMappingRow)
                .where(ProviderIdentityMappingRow.mapping_status == "VERIFIED")
            )
            == 0
        )


def test_us_sec_nasdaq_graph_reaches_ready_from_exact_filing_and_current_listing(
    database_context,
) -> None:
    _, _, result = _us_evaluation(database_context)
    assert result.machine_state == "READY_FOR_MANUAL_REVIEW"
    assert result.decision is not None
    assert result.bundle is not None
    assert "SEC_REGISTERED_CLASS" in result.bundle.proposed_anchor
    assert US_SYMBOL not in result.bundle.proposed_anchor
    assert {item.result for item in result.scope_results} == {"SATISFIED"}


def test_sec_accession_prefix_does_not_replace_verified_registrant_cik(
    database_context,
) -> None:
    harness, _, result = _us_evaluation(
        database_context,
        accepted_accession="0000123456-26-000003",
    )

    assert result.machine_state == "READY_FOR_MANUAL_REVIEW"
    assert result.bundle is not None
    assert f"SEC_REGISTERED_CLASS|{US_CIK}/0000123456-26-000003/sha256:" in (
        result.bundle.proposed_anchor
    )
    with session_factory(database_context.engine)() as session:
        members = session.scalars(
            select(SecurityBundleProviderObservationRow).where(
                SecurityBundleProviderObservationRow.bundle_id == result.bundle.bundle_id
            )
        ).all()
    assert len(members) == 1
    member = c.BundleProviderObservation.model_validate_json(members[0].payload_json)
    assert member.provider_id == harness.provider_id
    assert member.observation_id == harness.provider_observation_id


def test_exchange_only_us_evidence_cannot_reach_ready(database_context) -> None:
    harness = _us_harness(database_context)
    _approve_issuer(database_context, harness, _us_request(harness))
    _us_base_facts(database_context, include_sec=False)

    result = SecurityAuthorityDecisionEngine(
        session_factory(database_context.engine), clock=lambda: EVALUATED_AT
    ).evaluate(SecurityAuthorityEvaluationRequest(provider_id=harness.provider_id))

    assert result.machine_state == "UNRESOLVED"
    assert "SECURITY_ANCHOR_UNAVAILABLE" in result.reason_codes


def test_us_class_title_and_ticker_disagreement_block_ready(database_context) -> None:
    harness = _us_harness(database_context)
    _approve_issuer(database_context, harness, _us_request(harness))
    _us_base_facts(
        database_context,
        nasdaq_security_name="Preferred Stock",
        exchange_symbol="OTHER",
    )

    result = SecurityAuthorityDecisionEngine(
        session_factory(database_context.engine), clock=lambda: EVALUATED_AT
    ).evaluate(SecurityAuthorityEvaluationRequest(provider_id=harness.provider_id))

    assert result.machine_state != "READY_FOR_MANUAL_REVIEW"


@pytest.mark.parametrize(
    "registered_class_title",
    ["Preferred Stock", "American Depositary Shares", "ETF", "ETN", "Warrant"],
)
def test_us_unsupported_instrument_families_cannot_reach_ready(
    database_context, registered_class_title: str
) -> None:
    _, _, result = _us_evaluation(
        database_context,
        registered_class_title=registered_class_title,
    )

    assert result.machine_state != "READY_FOR_MANUAL_REVIEW"


@pytest.mark.parametrize(
    "options,reason",
    [
        ({"provider_isin": "KR1000000008"}, "PROVIDER_ISIN_MISMATCH"),
        ({"issue_isin": "KR1000000008"}, "PROVIDER_ISIN_MISMATCH"),
        ({"stock_kind": "PREFERRED_EQUITY"}, "KRX_SHARE_KIND_UNSUPPORTED"),
        (
            {"listing_status": "DELISTED", "delisting_date": date(2026, 8, 1)},
            "KRX_NOT_CURRENTLY_LISTED",
        ),
        ({"dart_stock_code": "000001"}, "OPENDART_BRIDGE_MISMATCH"),
        (
            {"standard_source_as_of": EVALUATED_AT - timedelta(hours=97)},
            "REQUIRED_SOURCE_FRESHNESS_NOT_ESTABLISHED",
        ),
        (
            {"listing_retrieved_at": EVALUATED_AT - timedelta(hours=97)},
            "REQUIRED_SOURCE_FRESHNESS_NOT_ESTABLISHED",
        ),
        (
            {"dart_retrieved_at": EVALUATED_AT - timedelta(hours=49)},
            "REQUIRED_SOURCE_FRESHNESS_NOT_ESTABLISHED",
        ),
    ],
)
def test_kr_required_negative_paths_fail_closed(database_context, options, reason) -> None:
    fact_options = {key: value for key, value in options.items() if key != "provider_isin"}
    provider_isin = options.get("provider_isin", KR_ISIN)
    harness = _kr_harness(database_context, provider_isin=provider_isin)
    _approve_issuer(database_context, harness, _kr_request(harness))
    _kr_base_facts(database_context, **fact_options)
    result = SecurityAuthorityDecisionEngine(
        session_factory(database_context.engine), clock=lambda: EVALUATED_AT
    ).evaluate(SecurityAuthorityEvaluationRequest(provider_id=harness.provider_id))
    assert result.machine_state != "READY_FOR_MANUAL_REVIEW"
    assert reason in result.reason_codes


@pytest.mark.parametrize(
    "options,reason",
    [
        ({"exchange_name": "NYSE"}, "SEC_EXCHANGE_MISMATCH"),
        ({"registered_cik": "0000123456"}, "SECURITY_ANCHOR_UNAVAILABLE"),
        ({"exchange_symbol": "OTHER"}, "NASDAQ_PRIMARY_AUTHORITY_MISSING"),
        ({"registered_class_title": "Preferred Stock"}, "SEC_CLASS_UNSUPPORTED"),
        (
            {"sec_source_as_of": EVALUATED_AT - timedelta(hours=25)},
            "REQUIRED_SOURCE_FRESHNESS_NOT_ESTABLISHED",
        ),
        (
            {"nasdaq_file_time": EVALUATED_AT - timedelta(hours=37)},
            "REQUIRED_SOURCE_FRESHNESS_NOT_ESTABLISHED",
        ),
        ({"nasdaq_state": "ISSUE_DELETION"}, "NASDAQ_ISSUE_DELETION"),
        ({"nasdaq_state": "ISSUE_SUSPENSION"}, "NASDAQ_ISSUE_SUSPENSION"),
        ({"test_issue": True}, "NASDAQ_NOT_CURRENTLY_LISTED"),
        ({"form25": True}, "SEC_FORM_25_EFFECTIVE"),
    ],
)
def test_us_required_negative_paths_fail_closed(database_context, options, reason) -> None:
    harness = _us_harness(database_context)
    _approve_issuer(database_context, harness, _us_request(harness))
    _us_base_facts(database_context, **options)
    result = SecurityAuthorityDecisionEngine(
        session_factory(database_context.engine), clock=lambda: EVALUATED_AT
    ).evaluate(SecurityAuthorityEvaluationRequest(provider_id=harness.provider_id))
    assert result.machine_state != "READY_FOR_MANUAL_REVIEW"
    assert reason in result.reason_codes


def test_nyse_has_no_production_admission_and_cannot_reach_ready(database_context) -> None:
    assert (
        exact_policy_for(
            "NYSE_PRIMARY",
            "NYSE_SECURITY_MASTER",
            c.Scope.LISTING_VENUE,
            c.SubjectRole.EXCHANGE_ISSUE,
        )
        is None
    )
    harness = _us_harness(database_context)
    _approve_issuer(database_context, harness, _us_request(harness))
    _us_base_facts(database_context, exchange_name="NYSE", include_nasdaq=False)
    result = SecurityAuthorityDecisionEngine(
        session_factory(database_context.engine), clock=lambda: EVALUATED_AT
    ).evaluate(SecurityAuthorityEvaluationRequest(provider_id=harness.provider_id))
    assert result.machine_state == "UNRESOLVED"
    assert result.machine_state != "READY_FOR_MANUAL_REVIEW"


def test_identical_kr_replay_is_idempotent_and_does_not_fork_decision_chain(
    database_context,
) -> None:
    harness, engine, first = _kr_evaluation(database_context)
    second = engine.evaluate(SecurityAuthorityEvaluationRequest(provider_id=harness.provider_id))
    assert first.decision is not None and second.decision is not None
    assert first.decision.decision_id == second.decision.decision_id
    assert second.idempotent
    with session_factory(database_context.engine)() as session:
        decisions = session.scalar(select(func.count()).select_from(SecurityDecisionRow))
    assert decisions == 1


def test_malformed_source_subject_is_not_used_as_authority(database_context) -> None:
    harness = _kr_harness(database_context, provider_isin=KR_ISIN)
    _approve_issuer(database_context, harness, _kr_request(harness))
    _kr_base_facts(database_context)
    malformed = _source_fact(
        database_context,
        "KRX_ISSUE_BASIC",
        c.SubjectRole.KRX_ISSUE,
        KrxIssueBasicFact(
            stock_code=KR_SYMBOL,
            isin=KR_ISIN,
            market="KOSPI",
            ticker=KR_SYMBOL,
            security_type="STOCK",
            stock_kind="PREFERRED_EQUITY",
            listing_date=date(1975, 6, 11),
            nationality="KR",
        ),
        exact_subject="KRX_ISSUE:000002",
    )

    result = SecurityAuthorityDecisionEngine(
        session_factory(database_context.engine), clock=lambda: EVALUATED_AT
    ).evaluate(SecurityAuthorityEvaluationRequest(provider_id=harness.provider_id))

    assert result.machine_state == "READY_FOR_MANUAL_REVIEW"
    assert malformed.evidence_id not in {item.evidence_id for item in result.applications}


def test_correction_chain_uses_only_exact_current_head(database_context) -> None:
    harness = _kr_harness(database_context, provider_isin=KR_ISIN)
    _approve_issuer(database_context, harness, _kr_request(harness))
    original = _kr_base_facts(database_context, standard_isin=OLD_KR_ISIN)
    assert original is not None
    corrected = _source_fact(
        database_context,
        "KRX_STANDARD_CODE",
        c.SubjectRole.KRX_ISSUE,
        KrxStandardCodeFact(stock_code=KR_SYMBOL, isin=KR_ISIN),
        source_as_of=EVALUATED_AT - timedelta(minutes=5),
    )
    _relate_evidence(database_context, original, corrected)

    result = SecurityAuthorityDecisionEngine(
        session_factory(database_context.engine), clock=lambda: EVALUATED_AT
    ).evaluate(SecurityAuthorityEvaluationRequest(provider_id=harness.provider_id))

    assert result.machine_state == "READY_FOR_MANUAL_REVIEW"
    current_ids = {item.evidence_id for item in result.applications}
    assert corrected.evidence_id in current_ids
    assert original.evidence_id not in current_ids


def test_forked_correction_chain_fails_closed(database_context) -> None:
    harness = _kr_harness(database_context, provider_isin=KR_ISIN)
    _approve_issuer(database_context, harness, _kr_request(harness))
    original = _kr_base_facts(database_context, standard_isin=OLD_KR_ISIN)
    assert original is not None
    first = _source_fact(
        database_context,
        "KRX_STANDARD_CODE",
        c.SubjectRole.KRX_ISSUE,
        KrxStandardCodeFact(stock_code=KR_SYMBOL, isin=KR_ISIN),
    )
    second = _source_fact(
        database_context,
        "KRX_STANDARD_CODE",
        c.SubjectRole.KRX_ISSUE,
        KrxStandardCodeFact(stock_code=KR_SYMBOL, isin="KR7005931001"),
    )
    _relate_evidence(database_context, original, first)
    _relate_evidence(database_context, original, second)

    result = SecurityAuthorityDecisionEngine(
        session_factory(database_context.engine), clock=lambda: EVALUATED_AT
    ).evaluate(SecurityAuthorityEvaluationRequest(provider_id=harness.provider_id))

    assert result.machine_state == "REVIEW_REQUIRED"
    assert "EVIDENCE_RELATION_CONFLICT" in result.reason_codes
    assert result.machine_state != "READY_FOR_MANUAL_REVIEW"


def test_correction_cannot_cross_source_subject(database_context) -> None:
    harness = _kr_harness(database_context, provider_isin=KR_ISIN)
    _approve_issuer(database_context, harness, _kr_request(harness))
    original = _kr_base_facts(database_context, standard_isin=OLD_KR_ISIN)
    assert original is not None
    wrong_subject = _source_fact(
        database_context,
        "KRX_STANDARD_CODE",
        c.SubjectRole.KRX_ISSUE,
        KrxStandardCodeFact(stock_code="000002", isin="KR7005931001"),
    )
    _relate_evidence(database_context, original, wrong_subject)

    result = SecurityAuthorityDecisionEngine(
        session_factory(database_context.engine), clock=lambda: EVALUATED_AT
    ).evaluate(SecurityAuthorityEvaluationRequest(provider_id=harness.provider_id))

    assert result.machine_state == "REVIEW_REQUIRED"
    assert "EVIDENCE_RELATION_CONFLICT" in result.reason_codes


def test_fixture_lineage_cannot_be_promoted_by_production_correction(database_context) -> None:
    harness = _kr_harness(database_context, provider_isin=KR_ISIN)
    _approve_issuer(database_context, harness, _kr_request(harness))
    production_head = _kr_base_facts(database_context)
    assert production_head is not None
    fixture_predecessor = _source_fact(
        database_context,
        "KRX_STANDARD_CODE",
        c.SubjectRole.KRX_ISSUE,
        KrxStandardCodeFact(stock_code=KR_SYMBOL, isin=OLD_KR_ISIN),
        origin_mode="TEST_ONLY",
        fixture_taint=1,
        test_taint=1,
    )
    with pytest.raises(IntegrityError, match="trg_0008_relation_taint"):
        _relate_evidence(database_context, fixture_predecessor, production_head)

    result = SecurityAuthorityDecisionEngine(
        session_factory(database_context.engine), clock=lambda: EVALUATED_AT
    ).evaluate(SecurityAuthorityEvaluationRequest(provider_id=harness.provider_id))

    assert result.machine_state == "READY_FOR_MANUAL_REVIEW"
    assert fixture_predecessor.evidence_id not in {item.evidence_id for item in result.applications}


def test_tainted_newer_krx_fact_cannot_refresh_stale_authority(database_context) -> None:
    harness = _kr_harness(database_context, provider_isin=KR_ISIN)
    _approve_issuer(database_context, harness, _kr_request(harness))
    _kr_base_facts(
        database_context,
        standard_source_as_of=EVALUATED_AT - timedelta(hours=97),
    )
    tainted = _source_fact(
        database_context,
        "KRX_STANDARD_CODE",
        c.SubjectRole.KRX_ISSUE,
        KrxStandardCodeFact(stock_code=KR_SYMBOL, isin=OLD_KR_ISIN),
        source_as_of=EVALUATED_AT - timedelta(minutes=5),
        origin_mode="TEST_ONLY",
        fixture_taint=1,
        test_taint=1,
    )

    result = SecurityAuthorityDecisionEngine(
        session_factory(database_context.engine), clock=lambda: EVALUATED_AT
    ).evaluate(SecurityAuthorityEvaluationRequest(provider_id=harness.provider_id))

    assert result.machine_state == "STALE"
    assert "REQUIRED_SOURCE_FRESHNESS_NOT_ESTABLISHED" in result.reason_codes
    assert tainted.evidence_id not in {item.evidence_id for item in result.applications}


def test_issuer_without_current_approved_head_cannot_reach_ready(database_context) -> None:
    harness = _kr_harness(database_context, provider_isin=KR_ISIN)
    _kr_base_facts(database_context)

    result = SecurityAuthorityDecisionEngine(
        session_factory(database_context.engine), clock=lambda: EVALUATED_AT
    ).evaluate(SecurityAuthorityEvaluationRequest(provider_id=harness.provider_id))

    assert result.machine_state == "UNRESOLVED"
    assert "APPROVED_ISSUER_HEAD_MISSING" in result.reason_codes


@pytest.mark.parametrize("provider_isin", [None, KR_ISIN], ids=["name-only", "ticker-only"])
def test_provider_observation_alone_cannot_identify_kr_security(
    database_context, provider_isin: str | None
) -> None:
    harness = _kr_harness(database_context, provider_isin=provider_isin)
    _approve_issuer(database_context, harness, _kr_request(harness))

    result = SecurityAuthorityDecisionEngine(
        session_factory(database_context.engine), clock=lambda: EVALUATED_AT
    ).evaluate(SecurityAuthorityEvaluationRequest(provider_id=harness.provider_id))

    assert result.machine_state == "UNRESOLVED"
    assert "SECURITY_ANCHOR_UNAVAILABLE" in result.reason_codes
    assert result.applications == ()


def test_missing_kr_standard_identifier_is_unresolved(database_context) -> None:
    harness = _kr_harness(database_context, provider_isin=KR_ISIN)
    _approve_issuer(database_context, harness, _kr_request(harness))
    _kr_base_facts(database_context, include_standard=False)

    result = SecurityAuthorityDecisionEngine(
        session_factory(database_context.engine), clock=lambda: EVALUATED_AT
    ).evaluate(SecurityAuthorityEvaluationRequest(provider_id=harness.provider_id))

    assert result.machine_state == "UNRESOLVED"
    assert result.machine_state != "READY_FOR_MANUAL_REVIEW"


def test_missing_kr_listing_lifecycle_blocks_ready(database_context) -> None:
    harness = _kr_harness(database_context, provider_isin=KR_ISIN)
    _approve_issuer(database_context, harness, _kr_request(harness))
    _kr_base_facts(database_context, include_listing=False)

    result = SecurityAuthorityDecisionEngine(
        session_factory(database_context.engine), clock=lambda: EVALUATED_AT
    ).evaluate(SecurityAuthorityEvaluationRequest(provider_id=harness.provider_id))

    assert result.machine_state != "READY_FOR_MANUAL_REVIEW"
    assert any(
        scope.scope == c.Scope.LISTING_STATUS and scope.result == "MISSING"
        for scope in result.scope_results
    )


def test_ambiguous_current_kr_issue_rows_require_review(database_context) -> None:
    harness = _kr_harness(database_context, provider_isin=KR_ISIN)
    _approve_issuer(database_context, harness, _kr_request(harness))
    _kr_base_facts(database_context)
    _source_fact(
        database_context,
        "KRX_ISSUE_BASIC",
        c.SubjectRole.KRX_ISSUE,
        KrxIssueBasicFact(
            stock_code=KR_SYMBOL,
            isin=KR_ISIN,
            market="KOSPI",
            ticker=KR_SYMBOL,
            security_type="STOCK",
            stock_kind="PREFERRED_EQUITY",
            listing_date=date(1975, 6, 11),
            nationality="KR",
        ),
    )

    result = SecurityAuthorityDecisionEngine(
        session_factory(database_context.engine), clock=lambda: EVALUATED_AT
    ).evaluate(SecurityAuthorityEvaluationRequest(provider_id=harness.provider_id))

    assert result.machine_state == "REVIEW_REQUIRED"
    assert result.machine_state != "READY_FOR_MANUAL_REVIEW"


def test_fresh_to_stale_transition_appends_new_decision(database_context) -> None:
    harness, engine, first = _kr_evaluation(database_context)
    assert first.decision is not None
    stale_engine = SecurityAuthorityDecisionEngine(
        session_factory(database_context.engine),
        clock=lambda: EVALUATED_AT + timedelta(hours=97),
    )

    second = stale_engine.evaluate(
        SecurityAuthorityEvaluationRequest(provider_id=harness.provider_id)
    )

    assert second.machine_state == "STALE"
    assert second.decision is not None
    assert second.decision.decision_id != first.decision.decision_id
    assert second.decision.supersedes_decision_id == first.decision.decision_id
    with session_factory(database_context.engine)() as session:
        assert session.scalar(select(func.count()).select_from(SecurityDecisionRow)) == 2


def test_later_krx_identifier_contradiction_supersedes_ready(database_context) -> None:
    harness, engine, first = _kr_evaluation(database_context)
    assert first.machine_state == "READY_FOR_MANUAL_REVIEW"
    assert first.decision is not None
    _source_fact(
        database_context,
        "KRX_STANDARD_CODE",
        c.SubjectRole.KRX_ISSUE,
        KrxStandardCodeFact(stock_code=KR_SYMBOL, isin="KR7000660001"),
        source_as_of=EVALUATED_AT - timedelta(minutes=10),
    )

    second = engine.evaluate(SecurityAuthorityEvaluationRequest(provider_id=harness.provider_id))

    assert second.machine_state == "REVIEW_REQUIRED"
    assert "KRX_STANDARD_CODE_CONTRADICTION" in second.reason_codes
    assert second.decision is not None
    assert second.decision.supersedes_decision_id == first.decision.decision_id
    with session_factory(database_context.engine)() as session:
        rows = session.scalars(select(SecurityDecisionRow)).all()
        superseded = {
            row.supersedes_decision_id for row in rows if row.supersedes_decision_id is not None
        }
        leaves = [row for row in rows if row.decision_id not in superseded]
        assert len(leaves) == 1
        assert leaves[0].machine_state == "REVIEW_REQUIRED"


def test_collision_quarantines_every_provider_candidate(database_context) -> None:
    first = _kr_harness(
        database_context,
        label="c2_collision_first",
        provider_isin=KR_ISIN,
    )
    authenticator = _approve_issuer(database_context, first, _kr_request(first))
    _kr_base_facts(database_context)
    first_result = SecurityAuthorityDecisionEngine(
        session_factory(database_context.engine), clock=lambda: EVALUATED_AT
    ).evaluate(SecurityAuthorityEvaluationRequest(provider_id=first.provider_id))
    assert first_result.machine_state == "READY_FOR_MANUAL_REVIEW"

    second_corp_code = "99999999"
    second = _kr_harness(
        database_context,
        label="c2_collision_second",
        corp_code=second_corp_code,
        overview_jurir="1102220000000",
        iros_jurir="1102220000000",
        opendart_legal_name="Collision legal issuer",
        iros_legal_name="Collision legal issuer",
        provider_isin=KR_ISIN,
    )
    _approve_issuer(
        database_context,
        second,
        _kr_request(second, identifier_value=second_corp_code),
        authenticator=authenticator,
        assertion_count=10,
    )
    _kr_base_facts(
        database_context,
        dart_corp_code=second_corp_code,
        include_standard=False,
        include_issue=False,
        include_listing=False,
    )
    second_result = SecurityAuthorityDecisionEngine(
        session_factory(database_context.engine), clock=lambda: EVALUATED_AT
    ).evaluate(SecurityAuthorityEvaluationRequest(provider_id=second.provider_id))

    assert second_result.machine_state == "REVIEW_REQUIRED"
    assert second_result.collision.result == "CONFLICT"
    assert {first.provider_id, second.provider_id}.issubset(
        set(second_result.affected_provider_ids)
    )


def test_concurrent_positive_evaluations_share_one_decision_successor(database_context) -> None:
    harness = _kr_harness(database_context, provider_isin=KR_ISIN)
    _approve_issuer(database_context, harness, _kr_request(harness))
    _kr_base_facts(database_context)
    barrier = Barrier(2)

    def evaluate() -> Any:
        barrier.wait()
        return SecurityAuthorityDecisionEngine(
            session_factory(database_context.engine), clock=lambda: EVALUATED_AT
        ).evaluate(SecurityAuthorityEvaluationRequest(provider_id=harness.provider_id))

    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = pool.map(lambda _: evaluate(), range(2))

    assert first.decision is not None and second.decision is not None
    assert first.decision.decision_id == second.decision.decision_id
    with session_factory(database_context.engine)() as session:
        assert session.scalar(select(func.count()).select_from(SecurityDecisionRow)) == 1


def test_global_duplicate_active_isin_quarantines_candidate(database_context) -> None:
    harness = _kr_harness(database_context, provider_isin=KR_ISIN)
    _approve_issuer(database_context, harness, _kr_request(harness))
    _kr_base_facts(database_context)
    _source_fact(
        database_context,
        "KRX_STANDARD_CODE",
        c.SubjectRole.KRX_ISSUE,
        KrxStandardCodeFact(stock_code="000001", isin=KR_ISIN),
        source_as_of=EVALUATED_AT - timedelta(minutes=30),
    )
    result = SecurityAuthorityDecisionEngine(
        session_factory(database_context.engine), clock=lambda: EVALUATED_AT
    ).evaluate(SecurityAuthorityEvaluationRequest(provider_id=harness.provider_id))
    assert result.machine_state == "REVIEW_REQUIRED"
    assert result.collision.result == "CONFLICT"
    assert "DUPLICATE_ACTIVE_ISIN_AUTHORITY" in result.collision.reason_codes


def test_registry_excludes_cgs_and_arbitrary_source_admission() -> None:
    assert all(
        spec.ingestion == "HUMAN_ASSISTED_VERIFIED_DOCUMENT"
        for spec in SOURCE_POLICY_SPECS
        if spec.namespace.startswith("KRX_")
    )
    assert (
        exact_policy_for(
            "CGS", "CUSIP_MASTER", c.Scope.SECURITY_IDENTIFIER, c.SubjectRole.EXCHANGE_ISSUE
        )
        is None
    )
    assert (
        exact_policy_for(
            "KRX_STANDARD_CODE", "*", c.Scope.SECURITY_IDENTIFIER, c.SubjectRole.KRX_ISSUE
        )
        is None
    )
    assert (
        exact_policy_for(
            "TOSS_PROVIDER_OBSERVATION",
            "PROVIDER_SECURITY_MASTER",
            c.Scope.SECURITY_IDENTIFIER,
            c.SubjectRole.PROVIDER_SUBJECT,
        )
        is None
    )
    assert (
        exact_policy_for(
            "TOSS_PROVIDER_OBSERVATION",
            "PROVIDER_SECURITY_MASTER",
            c.Scope.PROVIDER_SECURITY_BRIDGE,
            c.SubjectRole.PROVIDER_SUBJECT,
        )
        is not None
    )
