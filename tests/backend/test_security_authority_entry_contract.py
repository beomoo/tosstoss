"""C3-entry compatibility only. All Security approval/link rows are synthetic SQL fixtures."""

from datetime import timedelta

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from tests.backend import test_security_authority_decision_engine as support
from tests.backend.security_authority_test_support import authorization, business, insert, record
from tests.backend.test_security_authority_remediation import evaluate, prepare, reseal

from toss_dashboard_api.contracts import security_authority as c
from toss_dashboard_api.contracts.security_authority_decision import (
    SecurityAuthorityEvaluationRequest,
)
from toss_dashboard_api.domain.security_authority import (
    SecurityAuthorityDecisionEngine,
    SecurityAuthorityDecisionEngineError,
)
from toss_dashboard_api.storage.database import session_factory


def profile_for(result, **changes):
    return c.proposed_authority_profile(
        **(
            dict(
                provider_id=result.bundle.provider_id,
                issuer_id=result.bundle.issuer_id,
                anchor=result.bundle.proposed_anchor,
                applications=result.applications,
                claims=(*result.identifier_claims, *result.class_claims, *result.listing_claims),
                profile_id="synthetic_profile",
                recorded_at=support.EVALUATED_AT,
            )
            | changes
        )
    )


def synthetic_profile_and_link(context, result):
    """Exercise both frozen link FKs, without claiming real Security WebAuthn."""
    bundle, decision = result.bundle, result.decision
    profile = profile_for(result)
    with context.engine.begin() as connection:
        insert(
            connection,
            record(
                c.CanonicalSubject,
                security_id=bundle.security_id,
                issuer_id=bundle.issuer_id,
                founding_anchor=bundle.proposed_anchor,
                anchor_kind=bundle.proposed_anchor.split("|")[2],
                anchor_hash=c.security_hash(bundle.proposed_anchor),
            ),
        )
        insert(connection, profile)
        issuer = {
            "principal": dict(
                connection.exec_driver_sql("SELECT * FROM reviewer_principals").mappings().one()
            ),
            "credential": dict(
                connection.exec_driver_sql("SELECT * FROM reviewer_webauthn_credentials")
                .mappings()
                .one()
            ),
        }
        graph = dict(
            binding={
                key: getattr(bundle, key) for key in ("provider_id", "issuer_id", "security_id")
            },
            issuer_binding={
                key: getattr(bundle, key)
                for key in (
                    "issuer_link_id",
                    "issuer_link_hash",
                    "issuer_link_state",
                    "issuer_head_state_hash",
                )
            },
            decision=decision,
            profile=profile,
        )
        auth = authorization(connection, issuer, graph, "synthetic_entry")
        rows = business(connection, graph, auth, "synthetic_entry")
        assert rows["link"].profile_hash == bundle.profile_hash == profile.content_hash
        assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
        assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []
    return profile


@pytest.mark.parametrize("jurisdiction", ["KR", "US"])
def test_exact_profile_and_both_link_fks_from_real_c2_graph(database_context, jurisdiction):
    run = support._kr_evaluation if jurisdiction == "KR" else support._us_evaluation
    _, engine, result = run(database_context)
    assert result.machine_state == "READY_FOR_MANUAL_REVIEW"
    profile = profile_for(result)
    assert profile.content_hash == result.bundle.profile_hash
    assert (
        profile_for(
            result, profile_id="later_profile", recorded_at=support.EVALUATED_AT + timedelta(days=1)
        ).content_hash
        == profile.content_hash
    )
    assert len(result.listing_claims) >= 3  # Supporting venue/status evidence is retained.
    assert len(result.identifier_claims) == 1
    identifier = result.identifier_claims[0]
    app = next(a for a in result.applications if a.application_id == identifier.application_id)
    assert identifier.application_hash == app.content_hash
    assert app.status == "ADMITTED" and app.requested_weight == 3
    if jurisdiction == "US":
        assert identifier.contract_version == "security-identifier-claim/0.2.0"
        assert app.source_namespace == "SEC_ACCEPTED_8A"
        assert app.scope == "IDENTIFIER_PROVENANCE"
        assert identifier.identifier_value == result.bundle.proposed_anchor.split("|")[3]
    else:
        assert app.source_namespace == "KRX_STANDARD_CODE"
        assert identifier.contract_version == "security-identifier-claim/0.1.0"
    # Same current evidence is stable, and C2 has not written any canonical/human rows.
    again = engine.evaluate(
        SecurityAuthorityEvaluationRequest(provider_id=result.bundle.provider_id)
    )
    assert again.decision == result.decision
    with database_context.engine.connect() as connection:
        for table in (
            "canonical_security_subjects",
            "security_authority_profiles",
            "security_approval_events",
            "security_authority_links",
        ):
            assert connection.exec_driver_sql(f"SELECT count(*) FROM {table}").scalar_one() == 0
    synthetic_profile_and_link(database_context, result)
    with pytest.raises(ValidationError, match="content hash"):
        c.AuthorityProfile.model_validate_json(
            c.canonical_security_bytes(
                profile.model_copy(update={"content_hash": c.security_hash("forged")})
            )
        )


@pytest.mark.parametrize(
    "kind,scope",
    [
        ("SEC_REGISTERED_CLASS", "SECURITY_IDENTIFIER"),
        ("SEC_REGISTERED_CLASS", "REGISTERED_CLASS"),
        ("KRX_ISIN", "IDENTIFIER_PROVENANCE"),
        ("KRX_ISIN", "LISTING_INTERVAL"),
        ("KRX_ISIN", "ARBITRARY"),
    ],
)
def test_v02_illegal_identifier_pairs_contract_and_sql(database_context, kind, scope):
    _, _, result = support._us_evaluation(database_context)
    claim = result.identifier_claims[0]
    with pytest.raises(ValidationError):
        reseal(claim, identifier_kind=kind, scope=scope)
    with database_context.engine.begin() as connection:
        with pytest.raises(IntegrityError):
            with connection.begin_nested():
                insert(
                    connection, claim, claim_id="illegal_pair", identifier_kind=kind, scope=scope
                )
        assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []


@pytest.mark.parametrize("wrong", ["class_application", "scope", "hash", "owner_source"])
def test_us_identifier_requires_exact_provenance_application(database_context, wrong):
    _, _, result = support._us_evaluation(database_context)
    claim = result.identifier_claims[0]
    app = next(a for a in result.applications if a.application_id == claim.application_id)
    changes = {"claim_id": "wrong_application"}
    if wrong == "class_application":
        app = next(
            a
            for a in result.applications
            if a.scope == "REGISTERED_CLASS" and a.source_namespace == "SEC_ACCEPTED_8A"
        )
        changes.update(application_id=app.application_id, application_hash=app.content_hash)
    elif wrong == "scope":
        changes["scope"] = "SECURITY_IDENTIFIER"
    elif wrong == "hash":
        changes["application_hash"] = c.security_hash("wrong")
    else:
        # A different admitted owner application is not SEC registered-class provenance.
        app = next(a for a in result.applications if a.scope == "LISTING_INTERVAL")
        changes.update(application_id=app.application_id, application_hash=app.content_hash)
    with database_context.engine.begin() as connection:
        with pytest.raises(IntegrityError):
            with connection.begin_nested():
                insert(connection, claim, **changes)


def test_v02_kr_claim_is_legal_without_rewriting_v01(database_context):
    _, _, result = support._kr_evaluation(database_context)
    old = result.identifier_claims[0]
    upgraded = reseal(
        old, claim_id="v02_kr_identifier", contract_version="security-identifier-claim/0.2.0"
    )
    with database_context.engine.begin() as connection:
        before = connection.exec_driver_sql(
            "SELECT * FROM security_identifier_claims WHERE claim_id=?", (old.claim_id,)
        ).all()
        insert(connection, upgraded)
        assert (
            connection.exec_driver_sql(
                "SELECT * FROM security_identifier_claims WHERE claim_id=?", (old.claim_id,)
            ).all()
            == before
        )
        assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []
    assert c.IdentifierClaim.model_validate_json(old.model_dump_json()) == old
    with pytest.raises(ValidationError):
        reseal(old, scope="IDENTIFIER_PROVENANCE")


def rebind_bundle(graph, bundle):
    graph["bundle"] = bundle
    for key in ("bundle_applications", "scopes", "providers"):
        graph[key] = tuple(
            reseal(item, bundle_id=bundle.bundle_id, bundle_hash=bundle.content_hash)
            for item in graph[key]
        )
    graph["decision"] = reseal(
        graph["decision"], bundle_id=bundle.bundle_id, bundle_hash=bundle.content_hash
    )


@pytest.mark.parametrize(
    "corruption",
    [
        "identifier_value",
        "identifier_hash",
        "class",
        "listing_interval",
        "support_listing",
        "ambiguous_owner",
        "forged_bundle_hash",
        "application_scope",
        "missing_identifier",
    ],
)
@pytest.mark.parametrize("jurisdiction", ["KR", "US"])
def test_repository_independent_profile_ready_backstop(
    database_context, monkeypatch, jurisdiction, corruption
):
    harness, _ = prepare(database_context, jurisdiction)
    (support._kr_base_facts if jurisdiction == "KR" else support._us_base_facts)(database_context)
    engine = SecurityAuthorityDecisionEngine(
        session_factory(database_context.engine), clock=lambda: support.EVALUATED_AT
    )
    persist = engine._repository.insert_machine_evaluation

    def corrupt(session, **graph):
        profile = c.proposed_authority_profile(
            provider_id=graph["bundle"].provider_id,
            issuer_id=graph["bundle"].issuer_id,
            anchor=graph["bundle"].proposed_anchor,
            applications=graph["applications"],
            claims=graph["claims"],
            profile_id="attack_profile",
            recorded_at=support.EVALUATED_AT,
        )
        claims = list(graph["claims"])
        for index, claim in enumerate(claims):
            if isinstance(claim, c.IdentifierClaim):
                if corruption == "identifier_value":
                    claims[index] = reseal(claim, identifier_value="wrong-anchor-value")
                if corruption == "identifier_hash":
                    claims[index] = claim.model_copy(
                        update={"content_hash": c.security_hash("wrong")}
                    )
                if corruption == "application_scope":
                    claims[index] = reseal(claim, application_id=profile.class_claim_id)
            if isinstance(claim, c.ClassClaim) and corruption == "class":
                claims[index] = reseal(claim, authority_share_kind="PREFERRED")
            if isinstance(claim, c.ListingClaim) and claim.claim_id == profile.listing_claim_id:
                if corruption == "listing_interval":
                    claims[index] = reseal(claim, valid_from=claim.valid_from + timedelta(days=1))
                if corruption == "support_listing":
                    support_app = next(
                        app
                        for app in graph["applications"]
                        if app.status == "SUPPORT_ONLY" and app.scope.value.startswith("LISTING_")
                    )
                    claims[index] = reseal(
                        claim,
                        application_id=support_app.application_id,
                        application_hash=support_app.content_hash,
                        scope=support_app.scope.value,
                    )
                if corruption == "ambiguous_owner":
                    claims.append(reseal(claim, claim_id="ambiguous_interval", ticker="OTHER"))
                    break
        graph["claims"] = tuple(
            claim
            for claim in claims
            if claim is not None
            and not (corruption == "missing_identifier" and isinstance(claim, c.IdentifierClaim))
        )
        # Recompute every hash an attacker could legitimately seal; current-fact
        # reconstruction must still reject forged claim fields at the repository.
        try:
            altered = c.proposed_authority_profile(
                provider_id=graph["bundle"].provider_id,
                issuer_id=graph["bundle"].issuer_id,
                anchor=graph["bundle"].proposed_anchor,
                applications=graph["applications"],
                claims=graph["claims"],
                profile_id="altered_profile",
                recorded_at=support.EVALUATED_AT,
            ).content_hash
        except ValueError:
            altered = graph["bundle"].profile_hash
        if corruption == "forged_bundle_hash":
            altered = c.security_hash("manually-forged-bundle-profile")
        rebind_bundle(graph, reseal(graph["bundle"], profile_hash=altered))
        return persist(session, **graph)

    monkeypatch.setattr(engine._repository, "insert_machine_evaluation", corrupt)
    with pytest.raises((SecurityAuthorityDecisionEngineError, ValidationError)):
        engine.evaluate(SecurityAuthorityEvaluationRequest(provider_id=harness.provider_id))
    with database_context.engine.connect() as connection:
        assert (
            connection.exec_driver_sql("SELECT count(*) FROM security_decisions").scalar_one() == 0
        )


@pytest.mark.parametrize("jurisdiction", ["KR", "US"])
def test_historical_ready_is_immutable_and_gets_exact_profile_successor(
    database_context, monkeypatch, jurisdiction
):
    harness, _ = prepare(database_context, jurisdiction)
    (support._kr_base_facts if jurisdiction == "KR" else support._us_base_facts)(database_context)
    engine = SecurityAuthorityDecisionEngine(
        session_factory(database_context.engine), clock=lambda: support.EVALUATED_AT
    )
    captured = {}

    class CaptureOnly(Exception):
        pass

    def capture(session, **graph):
        captured.update(graph)
        raise CaptureOnly

    with monkeypatch.context() as patch:
        patch.setattr(engine._repository, "insert_machine_evaluation", capture)
        with pytest.raises(CaptureOnly):
            engine.evaluate(SecurityAuthorityEvaluationRequest(provider_id=harness.provider_id))
    # Exact baseline aggregate algorithm, no US identifier, immutable READY root.
    # Actual unmodified-baseline engine negative controls are separately retained.
    profile = c.proposed_authority_profile(
        provider_id=captured["bundle"].provider_id,
        issuer_id=captured["bundle"].issuer_id,
        anchor=captured["bundle"].proposed_anchor,
        applications=captured["applications"],
        claims=captured["claims"],
        profile_id="historical_profile",
        recorded_at=support.EVALUATED_AT,
    )
    listing = next(item for item in captured["claims"] if item.claim_id == profile.listing_claim_id)
    old_payload = dict(
        security_id=profile.security_id,
        anchor=captured["bundle"].proposed_anchor,
        instrument_family=profile.instrument_family.value,
        identifier=profile.identifier_value,
        venue=profile.venue,
        ticker=listing.ticker,
        listing_date=profile.valid_from,
        class_claims=sorted(
            item.content_hash for item in captured["claims"] if isinstance(item, c.ClassClaim)
        ),
        listing_claims=sorted(
            item.content_hash for item in captured["claims"] if isinstance(item, c.ListingClaim)
        ),
    )
    if jurisdiction == "US":
        klass = next(item for item in captured["claims"] if item.claim_id == profile.class_claim_id)
        old_payload.update(
            registered_class_title=klass.registered_class_title,
            registered_row_id=klass.registered_row_id,
            market="US",
        )
    old_bundle = reseal(
        captured["bundle"],
        bundle_id="historical_bundle",
        profile_hash=c.security_hash(old_payload),
    )
    rebind_bundle(captured, old_bundle)
    captured["decision"] = reseal(captured["decision"], decision_id="historical_ready")
    with database_context.engine.begin() as connection:
        for key in ("policies", "applications", "claims"):
            for value in captured[key]:
                if jurisdiction == "US" and isinstance(value, c.IdentifierClaim):
                    continue
                insert(connection, value)
        insert(connection, old_bundle)
        for key in ("bundle_applications", "scopes", "providers"):
            for value in captured[key]:
                insert(connection, value)
        insert(connection, captured["decision"])
        old_rows = (
            connection.exec_driver_sql("SELECT * FROM security_authority_bundles").all(),
            connection.exec_driver_sql("SELECT * FROM security_decisions").all(),
        )
    successor = evaluate(database_context, harness)
    assert successor.machine_state == "READY_FOR_MANUAL_REVIEW"
    assert successor.decision.supersedes_decision_id == "historical_ready"
    assert successor.bundle.bundle_id != old_bundle.bundle_id
    assert profile_for(successor).content_hash == successor.bundle.profile_hash
    with database_context.engine.connect() as connection:
        assert (
            connection.exec_driver_sql(
                "SELECT * FROM security_authority_bundles WHERE bundle_id='historical_bundle'"
            ).all()
            == old_rows[0]
        )
        assert (
            connection.exec_driver_sql(
                "SELECT * FROM security_decisions WHERE decision_id='historical_ready'"
            ).all()
            == old_rows[1]
        )
        assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []
    synthetic_profile_and_link(database_context, successor)
