"""Independent counterexamples for the combined C2 remediation boundary."""

from datetime import timedelta
from typing import Any

import pytest
from sqlalchemy import select
from tests.backend import test_authority_decision_engine as issuer_support
from tests.backend import test_security_authority_decision_engine as support
from tests.backend.reviewer_test_support import Clock
from tests.backend.test_reviewer_runtime import OWNER

from toss_dashboard_api.contracts import security_authority as c
from toss_dashboard_api.contracts.security_authority_decision import (
    NasdaqPrimaryFact,
    SecPeriodicCoverFact,
    SecurityAuthorityEvaluationRequest,
)
from toss_dashboard_api.domain.security_authority import (
    SecurityAuthorityDecisionEngine,
    SecurityAuthorityDecisionEngineError,
)
from toss_dashboard_api.reviewer.issuer_disposition import IssuerDispositionService
from toss_dashboard_api.reviewer.runtime import _Runtime
from toss_dashboard_api.storage.database import session_factory
from toss_dashboard_api.storage.models import (
    IssuerAuthorityLinkHeadRow,
    ProviderSecurityIdentityRow,
    ProviderSecurityMasterObservationRow,
)
from toss_dashboard_api.storage.security_authority_models import (
    SecurityDecisionRow,
    SecurityEvidenceRow,
)

READY = "READY_FOR_MANUAL_REVIEW"


def reseal(value, **changes):
    fields = value.model_dump(mode="python")
    fields.pop("content_hash")
    fields.pop("audit_hash")
    return c.seal_security_record(type(value), **(fields | changes))


def evaluate(context, harness):
    return SecurityAuthorityDecisionEngine(
        session_factory(context.engine), clock=lambda: support.EVALUATED_AT
    ).evaluate(SecurityAuthorityEvaluationRequest(provider_id=harness.provider_id))


def prepare(context, jurisdiction="KR"):
    harness = (
        support._kr_harness(context, provider_isin=support.KR_ISIN)
        if jurisdiction == "KR"
        else support._us_harness(context)
    )
    authenticator = support._approve_issuer(
        context,
        harness,
        support._kr_request(harness) if jurisdiction == "KR" else support._us_request(harness),
    )
    return harness, authenticator


def observation_filter(monkeypatch, *, missing=False, namespace=None):
    original = support.insert

    def insert(connection, value, **changes):
        if isinstance(value, c.EvidenceObservation):
            if missing:
                return
            if namespace is None or namespace in value.run_id:
                value = reseal(value, parser_version="unadmitted-parser/1")
        original(connection, value, **changes)

    monkeypatch.setattr(support, "insert", insert)


def fact_change(monkeypatch, namespace, **changes):
    original = support._source_fact

    def source_fact(context, source, role, fact, **options):
        if source == namespace:
            fact = fact.model_copy(update=changes)
        return original(context, source, role, fact, **options)

    monkeypatch.setattr(support, "_source_fact", source_fact)


def add_cover(
    context, *, venue="NASDAQ", title="Common Stock", cik=support.US_CIK, ticker=support.US_SYMBOL
):
    support._source_fact(
        context,
        "SEC_PERIODIC_COVER",
        c.SubjectRole.SEC_REGISTRANT,
        SecPeriodicCoverFact(
            registrant_cik=cik,
            accepted_accession="0000789019-26-000003",
            class_title=title,
            ticker=ticker,
            exchange_name=venue,
        ),
    )


def dual_us(context, monkeypatch, *, same_security=False):
    first, authenticator = prepare(context, "US")
    support._us_base_facts(context)
    before = evaluate(context, first)
    assert before.machine_state == READY
    if not same_security:
        monkeypatch.setattr(issuer_support, "US_STATE_ENTITY_NUMBER", "7654321")
    second = support._us_harness(
        context,
        label="other_provider",
        cik=support.US_CIK if same_security else "0000123456",
        sec_legal_name="Second Corporation" if not same_security else issuer_support.US_LEGAL_NAME,
        state_legal_name="Second Corporation"
        if not same_security
        else issuer_support.US_LEGAL_NAME,
        accession=issuer_support.US_ACCESSION if same_security else "0000123456-26-000001",
    )
    if same_security:
        # Re-publish the same exact B facts through supported correction heads.
        # Existing approved B history is retained; old machine claims stop being
        # current, allowing the second genuine disposition under frozen B rules.
        for key, prior in tuple(second.evidence.items()):
            policy = (
                issuer_support.SEC_ACCEPTED_FILING_POLICY
                if prior.authority_source_identifier.startswith("SEC")
                else issuer_support.US_STATE_REGISTRY_DE_POLICY
            )
            successor = issuer_support._evidence(
                policy=policy,
                document_kind=prior.source_document_kind,
                document_reference=prior.authority_document_reference,
                document_group=prior.authority_source_locator.removeprefix(
                    policy.credential_free_locator_roots[0]
                )
                + "-c2-correction",
                scope=prior.authority_scope,
                role=prior.subject_role,
                claim_field=prior.claim_field,
                value=prior.normalized_claim_value,
                raw_value=prior.raw_claim_value,
                evidence_kind=issuer_support.AuthorityEvidenceKind.CORRECTION,
                authority_accepted_at=prior.authority_accepted_at,
            )
            issuer_support._persist_evidence(
                second.repository, successor, fetched_at=issuer_support.CURRENT_FETCHED_AT
            )
            relation = issuer_support.build_authority_evidence_relation(
                predecessor_evidence_id=prior.evidence_id,
                successor_evidence_id=successor.evidence_id,
                relation_type=issuer_support.AuthorityEvidenceRelationType.CORRECTS,
                recorded_at=support.EVALUATED_AT,
                authority_effective_missing_reason=issuer_support.AuthorityTimeMissingReason.NOT_SUPPLIED_BY_AUTHORITY,
            )
            issuer_support.seed_preadmitted_authority_snapshot(
                second.sessions, relations=(relation,)
            )
            second.evidence[key] = successor
    support._approve_issuer(
        context,
        second,
        support._us_request(
            second, identifier_value=support.US_CIK if same_security else "0000123456"
        ),
        authenticator=authenticator,
        assertion_count=10,
    )
    if not same_security:
        support._us_base_facts(
            context,
            registered_cik="0000123456",
            accepted_accession="0000123456-26-000001",
            include_nasdaq=False,
        )
    return first, second


def run_counterexample(context, monkeypatch, case):
    """Also runnable against the untouched old engine for measured before/after evidence."""
    if case in (10, 11):
        first, second = dual_us(context, monkeypatch, same_security=case == 11)
        result = evaluate(context, second)
        with session_factory(context.engine)() as session:
            rows = session.scalars(select(SecurityDecisionRow)).all()
            superseded = {row.supersedes_decision_id for row in rows}
            leaves = {
                row.provider_id: row.machine_state
                for row in rows
                if row.decision_id not in superseded
            }
        reevaluated = evaluate(context, first)
        return result, {
            "other_state": reevaluated.machine_state,
            "other_security_id": reevaluated.security_id,
            "leaves_before_recheck": leaves,
            "providers": sorted((first.provider_id, second.provider_id)),
        }
    if case == 12:
        first, second = dual_us(context, monkeypatch)
        support._us_base_facts(context, include_sec=False, include_nasdaq=False, form25=True)
        with session_factory(context.engine)() as session:
            prior = c.Evidence.model_validate_json(
                session.scalars(
                    select(SecurityEvidenceRow).where(
                        SecurityEvidenceRow.source_namespace == "NASDAQ_PRIMARY"
                    )
                )
                .one()
                .payload_json
            )
        fact = NasdaqPrimaryFact.model_validate_json(prior.fact_value).model_copy(
            update={
                "listing_date": support.EVALUATED_AT.date(),
                "file_creation_time": support.EVALUATED_AT,
            }
        )
        successor = support._source_fact(
            context,
            "NASDAQ_PRIMARY",
            c.SubjectRole.EXCHANGE_ISSUE,
            fact,
            effective_date=support.EVALUATED_AT.date(),
        )
        support._relate_evidence(context, prior, successor)
        previous = evaluate(context, first)
        result = evaluate(context, second)
        return result, {"previous_state": previous.machine_state}
    jurisdiction = "US" if case in (4, 5, 6, 7, 12) else "KR"
    harness, authenticator = prepare(context, jurisdiction)
    if case in (1, 2):
        observation_filter(monkeypatch, missing=case == 1)
    if case in (3, 4):
        original = support.insert

        def exclude(connection, value, **changes):
            if isinstance(value, c.EvidenceObservation):
                evidence_json = connection.exec_driver_sql(
                    "SELECT payload_json FROM security_authority_evidence WHERE evidence_id=?",
                    (value.evidence_id,),
                ).scalar_one()
                namespace = "KRX_STANDARD_CODE" if case == 3 else "SEC_ACCEPTED_8A"
                if c.Evidence.model_validate_json(evidence_json).source_namespace == namespace:
                    value = reseal(value, parser_version="unadmitted-parser/1")
            original(connection, value, **changes)

        monkeypatch.setattr(support, "insert", exclude)
    if case == 8:
        fact_change(monkeypatch, "KRX_ISSUE_BASIC", security_type="ETF")
    if case == 9:
        fact_change(monkeypatch, "KRX_LISTING_LIFECYCLE", security_type="ETF")
    if jurisdiction == "KR":
        support._kr_base_facts(context)
    else:
        support._us_base_facts(context, form25=case in (5, 6, 12))
    if case == 6:
        with context.engine.begin() as connection:
            payload = connection.exec_driver_sql(
                "SELECT o.payload_json FROM security_authority_evidence_observations o "
                "JOIN security_authority_evidence e ON e.evidence_id=o.evidence_id "
                "WHERE e.source_namespace='SEC_ACCEPTED_25'"
            ).scalar_one()
            observation = c.EvidenceObservation.model_validate_json(payload)
            support.insert(
                connection,
                reseal(
                    observation,
                    observation_id="failed_refresh_c2",
                    access_result="FAILED",
                    retrieved_at=support.EVALUATED_AT + timedelta(minutes=1),
                    recorded_at=support.EVALUATED_AT + timedelta(minutes=1),
                ),
            )
    if case == 7:
        add_cover(context, venue="NYSE")
    if case in (13, 14):
        before = evaluate(context, harness)
        assert before.machine_state == READY
        if case == 13:
            runtime = _Runtime(
                context.engine, lambda: OWNER, Clock(support.EVALUATED_AT + timedelta(minutes=2))
            )
            service = IssuerDispositionService(runtime, harness.engine)
            challenge = service.issue_revocation(harness.provider_id)
            service.complete(
                challenge.challenge_id,
                authenticator.assertion(challenge.options, 10),
                structured_reason_code="HUMAN_REVOCATION",
                review_note="C2 regression",
            )
        else:
            with session_factory(context.engine).begin() as session:
                session.get(
                    ProviderSecurityIdentityRow, harness.provider_id
                ).identity_state = "INACTIVE"
    result = evaluate(context, harness)
    extra = {}
    if case in (13, 14):
        with session_factory(context.engine)() as session:
            rows = session.scalars(select(SecurityDecisionRow)).all()
            superseded = {row.supersedes_decision_id for row in rows}
            extra["leaf_states"] = [
                row.machine_state for row in rows if row.decision_id not in superseded
            ]
            extra["decisions"] = len(rows)
        extra["idempotent"] = evaluate(context, harness).idempotent
    return result, extra


@pytest.mark.parametrize("case", list(range(1, 15)))
def test_consolidated_counterexamples(database_context, monkeypatch, case):
    result, extra = run_counterexample(database_context, monkeypatch, case)
    if case in (11, 12):
        assert result.machine_state == READY
        assert result.collision.result == "CLEAR"
        if case == 11:
            assert extra["other_state"] == READY
            assert extra["other_security_id"] == result.security_id
        else:
            assert extra["previous_state"] != READY
    else:
        assert result.machine_state != READY
    if case == 10:
        assert result.collision.result == "CONFLICT"
        assert list(result.affected_provider_ids) == extra["providers"]
        assert extra["other_state"] != READY
        assert all(state != READY for state in extra["leaves_before_recheck"].values())
    if case in (13, 14):
        assert extra["leaf_states"] == [result.machine_state]
        assert extra["decisions"] == 2
        assert extra["idempotent"]


@pytest.mark.parametrize(
    "namespace",
    [
        "KRX_STANDARD_CODE",
        "KRX_ISSUE_BASIC",
        "KRX_LISTING_LIFECYCLE",
        "SEC_ACCEPTED_8A",
        "NASDAQ_PRIMARY",
    ],
)
def test_excluded_required_application_blocks_scopes(database_context, monkeypatch, namespace):
    jurisdiction = "KR" if namespace.startswith("KRX") else "US"
    harness, _ = prepare(database_context, jurisdiction)
    original = support.insert

    def exclude(connection, value, **changes):
        if isinstance(value, c.EvidenceObservation):
            row = connection.exec_driver_sql(
                "SELECT source_namespace FROM security_authority_evidence WHERE evidence_id=?",
                (value.evidence_id,),
            ).scalar_one()
            if row == namespace:
                value = reseal(value, parser_version="unadmitted-parser/1")
        original(connection, value, **changes)

    monkeypatch.setattr(support, "insert", exclude)
    (support._kr_base_facts if jurisdiction == "KR" else support._us_base_facts)(database_context)
    result = evaluate(database_context, harness)
    assert result.machine_state != READY
    assert any(scope.result != "SATISFIED" for scope in result.scope_results)


@pytest.mark.parametrize("missing", [True, False])
def test_us_missing_observations_or_unadmitted_parser(database_context, monkeypatch, missing):
    harness, _ = prepare(database_context, "US")
    observation_filter(monkeypatch, missing=missing)
    support._us_base_facts(database_context)
    result = evaluate(database_context, harness)
    assert result.machine_state != READY
    assert not result.applications


@pytest.mark.parametrize("security_type", ["ETF", "ETN", "WARRANT", "UNKNOWN", "PREFERRED"])
def test_kr_type_and_kind_joint_interpretation(database_context, monkeypatch, security_type):
    harness, _ = prepare(database_context)
    fact_change(monkeypatch, "KRX_ISSUE_BASIC", security_type=security_type)
    support._kr_base_facts(database_context)
    assert evaluate(database_context, harness).machine_state != READY


@pytest.mark.parametrize(
    "cover,expected_ready",
    [
        ({}, True),
        ({"venue": "NYSE"}, False),
        ({"title": "Preferred Stock"}, False),
        ({"cik": "0000123456"}, True),
        ({"title": "Preferred Stock", "ticker": "OTHER"}, True),
    ],
)
def test_periodic_cover_support_and_relevant_contradictions(
    database_context, cover, expected_ready
):
    harness, _ = prepare(database_context, "US")
    support._us_base_facts(database_context)
    add_cover(database_context, **cover)
    result = evaluate(database_context, harness)
    assert (result.machine_state == READY) == expected_ready
    assert all(
        app.status == "SUPPORT_ONLY"
        for app in result.applications
        if app.source_namespace == "SEC_PERIODIC_COVER"
    )


def test_provider_current_observation_loss_replay_and_restoration(database_context):
    harness, _ = prepare(database_context)
    support._kr_base_facts(database_context)
    before = evaluate(database_context, harness)
    other = support._kr_harness(
        database_context, label="other_source_version", provider_isin=support.KR_ISIN
    )
    sessions = session_factory(database_context.engine)
    with sessions.begin() as session:
        identity = session.get(ProviderSecurityIdentityRow, harness.provider_id)
        original = identity.latest_source_version_id
        identity.latest_source_version_id = session.get(
            ProviderSecurityIdentityRow, other.provider_id
        ).latest_source_version_id
    lost = evaluate(database_context, harness)
    assert lost.machine_state in ("STALE", "UNRESOLVED")
    assert lost.decision.supersedes_decision_id == before.decision.decision_id
    assert evaluate(database_context, harness).idempotent
    with sessions.begin() as session:
        session.get(
            ProviderSecurityIdentityRow, harness.provider_id
        ).latest_source_version_id = original
    restored = evaluate(database_context, harness)
    assert restored.machine_state == READY
    assert restored.decision.supersedes_decision_id == lost.decision.decision_id


def assert_negative_leaf(context, before, result, harness):
    assert result.machine_state != READY
    assert result.decision.supersedes_decision_id == before.decision.decision_id
    assert evaluate(context, harness).idempotent
    with session_factory(context.engine)() as session:
        rows = session.scalars(select(SecurityDecisionRow)).all()
        assert len(rows) == 2
        superseded = {row.supersedes_decision_id for row in rows}
        assert [row.machine_state for row in rows if row.decision_id not in superseded] == [
            result.machine_state
        ]
        assert session.get(SecurityDecisionRow, before.decision.decision_id).machine_state == READY


def test_issuer_review_required_appends_negative_successor(database_context):
    harness, _ = prepare(database_context)
    support._kr_base_facts(database_context)
    before = evaluate(database_context, harness)
    later = support.EVALUATED_AT + timedelta(hours=26)
    harness.clock.value = later
    service = IssuerDispositionService(
        _Runtime(database_context.engine, lambda: OWNER, Clock(later)), harness.engine
    )
    service.revalidate_current_link(harness.provider_id)
    with session_factory(database_context.engine)() as session:
        assert session.get(IssuerAuthorityLinkHeadRow, harness.provider_id).link_state == (
            "REVIEW_REQUIRED"
        )
    result = evaluate(database_context, harness)
    assert result.machine_state == "REVIEW_REQUIRED"
    assert_negative_leaf(database_context, before, result, harness)


def test_ineligible_provider_observation_appends_negative_successor(database_context):
    harness, _ = prepare(database_context)
    support._kr_base_facts(database_context)
    before = evaluate(database_context, harness)
    other = support._kr_harness(database_context, label="ineligible_source")
    sessions = session_factory(database_context.engine)
    with sessions.begin() as session:
        identity = session.get(ProviderSecurityIdentityRow, harness.provider_id)
        source_id = session.get(
            ProviderSecurityIdentityRow, other.provider_id
        ).latest_source_version_id
        observation = issuer_support.build_security_master_observation(
            source_version_id=source_id,
            normalized_record_id=None,
            provider_security_identity_id=harness.provider_id,
            provider=issuer_support.ProviderSystem.TOSS_OPEN_API,
            market=issuer_support.Market.KR,
            symbol=issuer_support.KR_SYMBOL,
            name="Ineligible provider observation",
            security_type=issuer_support.ProviderSecurityType.STOCK,
            is_common_share=True,
            isin=support.KR_ISIN,
            staging_state=issuer_support.ProviderSecurityMasterState.QUARANTINED,
            reconciliation_outcome=issuer_support.ProviderReconciliationOutcome.DETAIL_REJECTED,
            identity_state_after=issuer_support.ProviderIdentityState.ACTIVE,
            eligible_for_mapping=False,
            collision_identity_ids=(),
            reason_codes=("TEST_CURRENT_OBSERVATION_INELIGIBLE",),
        )
        session.add(
            ProviderSecurityMasterObservationRow(
                observation_id=observation.observation_id,
                source_version_id=source_id,
                normalized_record_id=None,
                provider_security_identity_id=harness.provider_id,
                provider=observation.provider.value,
                market=observation.market.value,
                symbol=observation.symbol,
                staging_state=observation.staging_state.value,
                reconciliation_outcome=observation.reconciliation_outcome.value,
                eligible_for_mapping=0,
                provider_contract_version=observation.provider_contract_version,
                payload_json=observation.model_dump_json(),
            )
        )
        identity.latest_source_version_id = source_id
    result = evaluate(database_context, harness)
    assert result.machine_state == "STALE"
    assert_negative_leaf(database_context, before, result, harness)


def test_required_evidence_loss_appends_negative_successor(database_context):
    harness, _ = prepare(database_context)
    support._kr_base_facts(database_context)
    before = evaluate(database_context, harness)
    with session_factory(database_context.engine)() as session:
        prior = c.Evidence.model_validate_json(
            session.scalars(
                select(SecurityEvidenceRow).where(
                    SecurityEvidenceRow.source_namespace == "KRX_STANDARD_CODE"
                )
            )
            .one()
            .payload_json
        )
    successor = reseal(prior, evidence_id="required_standard_malformed", fact_value="{}")
    with database_context.engine.begin() as connection:
        support.insert(connection, successor)
    support._relate_evidence(database_context, prior, successor)
    result = evaluate(database_context, harness)
    assert "SECURITY_ANCHOR_UNAVAILABLE" in result.reason_codes
    assert_negative_leaf(database_context, before, result, harness)


@pytest.mark.parametrize("version", ["adapter_version", "parser_version"])
def test_accepted_form25_survives_unadmitted_refresh(database_context, version):
    harness, _ = prepare(database_context, "US")
    support._us_base_facts(database_context)
    assert evaluate(database_context, harness).machine_state == READY
    support._us_base_facts(database_context, include_sec=False, include_nasdaq=False, form25=True)
    assert evaluate(database_context, harness).machine_state != READY
    with database_context.engine.begin() as connection:
        payload = connection.exec_driver_sql(
            "SELECT o.payload_json FROM security_authority_evidence_observations o "
            "JOIN security_authority_evidence e ON e.evidence_id=o.evidence_id "
            "WHERE e.source_namespace='SEC_ACCEPTED_25'"
        ).scalar_one()
        observation = c.EvidenceObservation.model_validate_json(payload)
        support.insert(
            connection,
            reseal(
                observation,
                observation_id="unadmitted_negative_refresh",
                retrieved_at=support.EVALUATED_AT + timedelta(minutes=1),
                recorded_at=support.EVALUATED_AT + timedelta(minutes=1),
                **{version: "unadmitted/1"},
            ),
        )
    result = evaluate(database_context, harness)
    assert result.machine_state != READY
    assert "SEC_FORM_25_EFFECTIVE" in result.reason_codes


@pytest.mark.parametrize(
    "corruption",
    [
        "missing_proof",
        "dangling_proof",
        "out_of_bundle",
        "policy_hash",
        "evidence_hash",
        "excluded",
        "stale",
        "collision",
        "provider",
        "unsupported",
        "class_conflict",
    ],
)
def test_repository_rejects_malformed_internal_ready(database_context, monkeypatch, corruption):
    harness, _ = prepare(database_context)
    support._kr_base_facts(database_context)
    engine = SecurityAuthorityDecisionEngine(
        session_factory(database_context.engine), clock=lambda: support.EVALUATED_AT
    )
    persist = engine._repository.insert_machine_evaluation

    def corrupt(session, **graph: Any):
        if corruption in ("missing_proof", "dangling_proof"):
            graph["scopes"] = tuple(
                reseal(
                    scope,
                    owner_application_ids=()
                    if corruption == "missing_proof"
                    else ("nonexistent_application",),
                )
                for scope in graph["scopes"]
            )
        elif corruption == "out_of_bundle":
            graph["bundle_applications"] = graph["bundle_applications"][1:]
        elif corruption in ("policy_hash", "evidence_hash"):
            graph["applications"] = (
                reseal(graph["applications"][0], **{corruption: "sha256:" + "f" * 64}),
                *graph["applications"][1:],
            )
        elif corruption == "excluded":
            graph["applications"] = ()
            graph["claims"] = ()
            graph["bundle_applications"] = ()
        elif corruption == "stale":
            payload = (
                session.connection()
                .exec_driver_sql(
                    "SELECT o.payload_json FROM security_authority_evidence_observations o "
                    "JOIN security_authority_evidence e ON e.evidence_id=o.evidence_id "
                    "WHERE e.source_namespace='KRX_ISSUE_BASIC'"
                )
                .scalar_one()
            )
            observation = c.EvidenceObservation.model_validate_json(payload)
            support.insert(
                session.connection(),
                reseal(
                    observation,
                    observation_id="stale_required_source",
                    retrieved_at=support.EVALUATED_AT + timedelta(minutes=1),
                    recorded_at=support.EVALUATED_AT + timedelta(minutes=1),
                    source_as_of=support.EVALUATED_AT - timedelta(days=10),
                ),
            )
        elif corruption == "collision":
            graph["decision"] = reseal(graph["decision"], collision_result="CONFLICT")
        elif corruption == "provider":
            graph["providers"] = ()
        elif corruption == "unsupported":
            graph["claims"] = tuple(
                reseal(claim, instrument_family="UNKNOWN")
                if isinstance(claim, c.ClassClaim)
                else claim
                for claim in graph["claims"]
            )
        elif corruption == "class_conflict":
            graph["claims"] = tuple(
                reseal(claim, authority_share_kind="PREFERRED")
                if isinstance(claim, c.ClassClaim)
                else claim
                for claim in graph["claims"]
            )
        membership_hash = c.security_hash(
            {
                "applications": sorted(
                    (item.application_id, item.application_hash)
                    for item in graph["bundle_applications"]
                ),
                "scopes": sorted(
                    (item.scope.value, item.result, item.reason_codes, item.owner_application_ids)
                    for item in graph["scopes"]
                ),
                "providers": sorted(
                    (item.observation_id, item.observation_hash) for item in graph["providers"]
                ),
            }
        )
        graph["bundle"] = reseal(graph["bundle"], membership_hash=membership_hash)
        for key in ("bundle_applications", "scopes", "providers"):
            graph[key] = tuple(
                reseal(item, bundle_hash=graph["bundle"].content_hash) for item in graph[key]
            )
        graph["decision"] = reseal(graph["decision"], bundle_hash=graph["bundle"].content_hash)
        return persist(session, **graph)

    monkeypatch.setattr(engine._repository, "insert_machine_evaluation", corrupt)
    with pytest.raises(SecurityAuthorityDecisionEngineError):
        engine.evaluate(SecurityAuthorityEvaluationRequest(provider_id=harness.provider_id))
    with session_factory(database_context.engine)() as session:
        assert not session.scalars(select(SecurityDecisionRow)).all()
