"""Synthetic, disposable 0008 graphs over actual 0001-0008 migrations."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, get_args

from sqlalchemy import Connection
from tests.backend.reviewer_test_support import Authenticator, Clock
from tests.backend.test_authority_decision_engine import EVALUATED_AT, _kr_harness, _kr_request
from tests.backend.test_reviewer_runtime import OWNER, enroll

from toss_dashboard_api.contracts import security_authority as c
from toss_dashboard_api.reviewer.issuer_disposition import IssuerDispositionService
from toss_dashboard_api.reviewer.runtime import _Runtime
from toss_dashboard_api.storage import security_authority_models as m

NOW = datetime(2026, 9, 29, 1, 2, 3, tzinfo=UTC)
HASH = c.security_hash("synthetic-0008-test-only")
TABLES = {
    c.SourcePolicy: m.SecuritySourcePolicyRow.__tablename__,
    c.Evidence: m.SecurityEvidenceRow.__tablename__,
    c.EvidenceObservation: m.SecurityEvidenceObservationRow.__tablename__,
    c.EvidenceRelation: m.SecurityEvidenceRelationRow.__tablename__,
    c.EvidenceApplication: m.SecurityEvidenceApplicationRow.__tablename__,
    c.Bundle: m.SecurityBundleRow.__tablename__,
    c.BundleApplication: m.SecurityBundleApplicationRow.__tablename__,
    c.BundleScopeResult: m.SecurityBundleScopeResultRow.__tablename__,
    c.BundleProviderObservation: m.SecurityBundleProviderObservationRow.__tablename__,
    c.IdentifierClaim: m.SecurityIdentifierClaimRow.__tablename__,
    c.ClassClaim: m.SecurityClassClaimRow.__tablename__,
    c.ListingClaim: m.SecurityListingClaimRow.__tablename__,
    c.Decision: m.SecurityDecisionRow.__tablename__,
    c.ApprovalChallenge: m.SecurityApprovalChallengeRow.__tablename__,
    c.ChallengeConsumption: m.SecurityChallengeConsumptionRow.__tablename__,
    c.AuthenticationEvent: m.SecurityAuthenticationEventRow.__tablename__,
    c.ApprovalEvent: m.SecurityApprovalEventRow.__tablename__,
    c.ApprovalEvidenceObservation: m.SecurityApprovalEvidenceObservationRow.__tablename__,
    c.SupersessionPair: m.SecuritySupersessionPairRow.__tablename__,
    c.CanonicalSubject: m.SecurityCanonicalSubjectRow.__tablename__,
    c.AuthorityProfile: m.SecurityAuthorityProfileRow.__tablename__,
    c.AuthorityLink: m.SecurityAuthorityLinkRow.__tablename__,
    c.AuthorityLinkHead: m.SecurityAuthorityLinkHeadRow.__tablename__,
}


def record[T: c.SecurityRecord](kind: type[T], **values: Any) -> T:
    return c.seal_security_record(
        kind,
        contract_version=get_args(kind.model_fields["contract_version"].annotation)[0],
        recorded_at=NOW,
        **values,
    )


def row(value: c.SecurityRecord) -> dict[str, Any]:
    payload = c.canonical_security_bytes(value).decode()
    data = c.strict_security_json(payload)
    for key, val in tuple(data.items()):
        if isinstance(val, list):
            data[key] = c.canonical_security_bytes(val).decode()
    data["payload_json"] = payload
    if isinstance(value, c.SupersessionPair):
        data.update(
            old_state="APPROVED",
            disposition_a="SUPERSEDED",
            disposition_b="APPROVED",
            terminal_a="SUCCEEDED",
            terminal_b="SUCCEEDED",
        )
    return data


def insert(connection: Connection, value: c.SecurityRecord, **changes: Any) -> None:
    data = row(value) | changes
    keys = list(data)
    connection.exec_driver_sql(
        f"INSERT INTO {TABLES[type(value)]} ({','.join(keys)}) VALUES "
        f"({','.join('?' for _ in keys)})",
        tuple(data[k] for k in keys),
    )


def approved_issuer(context: Any, *, no_counter: bool = False) -> dict[str, Any]:
    harness = _kr_harness(context)
    ready = harness.engine.evaluate(_kr_request(harness))
    runtime = _Runtime(context.engine, lambda: OWNER, Clock(EVALUATED_AT + timedelta(minutes=1)))
    authenticator = Authenticator()
    enroll(
        runtime,
        authenticator,
        registration_count=0 if no_counter else 7,
        assertion_count=0 if no_counter else 8,
    )
    service = IssuerDispositionService(runtime, harness.engine)
    challenge = service.issue(ready.decision.issuer_decision_id, "APPROVED")
    service.complete(
        challenge.challenge_id,
        authenticator.assertion(challenge.options, 0 if no_counter else 9),
        structured_reason_code="VERIFIED_EXACT_AUTHORITY",
        review_note="Synthetic schema fixture",
    )
    with context.engine.connect() as connection:
        link = dict(
            connection.exec_driver_sql(
                "SELECT * FROM issuer_authority_links WHERE provider_security_identity_id=?",
                (ready.bundle.provider_security_identity_id,),
            )
            .mappings()
            .one()
        )
        head = dict(
            connection.exec_driver_sql(
                "SELECT * FROM issuer_authority_link_heads WHERE provider_security_identity_id=?",
                (ready.bundle.provider_security_identity_id,),
            )
            .mappings()
            .one()
        )
        principal = dict(
            connection.exec_driver_sql("SELECT * FROM reviewer_principals").mappings().one()
        )
        credential = dict(
            connection.exec_driver_sql("SELECT * FROM reviewer_webauthn_credentials")
            .mappings()
            .one()
        )
        observation = dict(
            connection.exec_driver_sql(
                "SELECT * FROM provider_security_master_observations "
                "WHERE provider_security_identity_id=?",
                (link["provider_security_identity_id"],),
            )
            .mappings()
            .first()
        )
    return {
        "link": link,
        "head": head,
        "principal": principal,
        "credential": credential,
        "observation": observation,
    }


def policy(
    suffix: str = "identifier", scope: c.Scope = c.Scope.SECURITY_IDENTIFIER
) -> c.SourcePolicy:
    return record(
        c.SourcePolicy,
        policy_id="policy_" + suffix,
        source_namespace="KRX_STANDARD_CODE",
        authority_classification="UNVERIFIED",
        document_kind="SYNTHETIC_TEST_RECORD",
        scope=scope,
        subject_role=c.SubjectRole.KRX_ISSUE,
        policy_version="test-" + suffix,
        max_weight=0,
        ingestion_mode="TEST_ISOLATED_ONLY",
        adapter_version="test/1",
        parser_version="test/1",
        production_eligible=0,
        access_disposition="UNVERIFIED",
        license_disposition="UNVERIFIED",
        origin_mode="TEST_ONLY",
        fixture_taint=1,
        test_taint=1,
        credential_free_locator_root="fixture://security/",
        predecessor_policy_id=None,
    )


def candidate(
    connection: Connection,
    issuer: dict[str, Any],
    suffix: str = "old",
    predecessor: str | None = None,
    isin: str = "KR7005930003",
    *,
    persist_subjects: bool = True,
) -> dict[str, Any]:
    link = issuer["link"]
    anchor = c.kr_anchor(link["issuer_id"], isin)
    sid = c.security_id_for_anchor(anchor)
    binding = dict(
        provider_id=link["provider_security_identity_id"],
        issuer_id=link["issuer_id"],
        security_id=sid,
    )
    issuer_binding = dict(
        issuer_link_id=link["issuer_authority_link_id"],
        issuer_link_hash=link["link_content_hash"],
        issuer_link_state="APPROVED",
        issuer_head_state_hash=issuer["head"]["state_hash"],
    )
    p = policy(suffix)
    e = record(
        c.Evidence,
        evidence_id="evidence_" + suffix,
        source_namespace=p.source_namespace,
        document_kind=p.document_kind,
        accepted_document_identity="synthetic-document-" + suffix,
        raw_digest=HASH,
        subject_role=p.subject_role,
        exact_subject=isin,
        fact_key="ISIN",
        fact_value=isin,
        origin_mode="TEST_ONLY",
        fixture_taint=1,
        test_taint=1,
        effective_date=None,
        effective_date_missing_reason="NOT_SUPPLIED_BY_AUTHORITY",
    )
    obs = record(
        c.EvidenceObservation,
        observation_id="observation_" + suffix,
        evidence_id=e.evidence_id,
        evidence_hash=e.content_hash,
        adapter_version="test/1",
        parser_version="test/1",
        run_id="run_test",
        retrieved_at=NOW,
        source_as_of=None,
        source_as_of_missing_reason="NOT_SUPPLIED_BY_AUTHORITY",
        access_result="SUCCEEDED",
        raw_digest=HASH,
    )
    app = record(
        c.EvidenceApplication,
        application_id="application_" + suffix,
        **binding,
        evidence_id=e.evidence_id,
        evidence_hash=e.content_hash,
        policy_id=p.policy_id,
        policy_hash=p.content_hash,
        source_namespace=p.source_namespace,
        document_kind=p.document_kind,
        scope=p.scope,
        subject_role=p.subject_role,
        requested_weight=0,
        claim_target="ISIN",
        relation_head_hash=HASH,
        status="ADMITTED",
        fixture_taint=1,
        test_taint=1,
    )
    extra_records = []

    def scoped_application(label: str, scope: c.Scope, fact_key: str, fact_value: str):
        extra_policy = policy(suffix + "_" + label, scope)
        extra_evidence = record(
            c.Evidence,
            **e.model_dump(
                exclude={
                    "contract_version",
                    "content_hash",
                    "audit_hash",
                    "recorded_at",
                    "evidence_id",
                    "fact_key",
                    "fact_value",
                }
            ),
            evidence_id="evidence_" + suffix + "_" + label,
            fact_key=fact_key,
            fact_value=fact_value,
        )
        extra_application = record(
            c.EvidenceApplication,
            **app.model_dump(
                exclude={
                    "contract_version",
                    "content_hash",
                    "audit_hash",
                    "recorded_at",
                    "application_id",
                    "evidence_id",
                    "evidence_hash",
                    "policy_id",
                    "policy_hash",
                    "scope",
                    "claim_target",
                }
            ),
            application_id="application_" + suffix + "_" + label,
            evidence_id=extra_evidence.evidence_id,
            evidence_hash=extra_evidence.content_hash,
            policy_id=extra_policy.policy_id,
            policy_hash=extra_policy.content_hash,
            scope=scope,
            claim_target=fact_key,
        )
        extra_records.extend((extra_policy, extra_evidence, extra_application))
        return extra_application

    class_app = scoped_application("class", c.Scope.INSTRUMENT_CLASS, "SHARE_KIND", "COMMON")
    listing_app = scoped_application("listing", c.Scope.LISTING_VENUE, "VENUE", "KRX")

    def claim_binding(application):
        return dict(
            **binding,
            application_id=application.application_id,
            application_hash=application.content_hash,
            application_status="ADMITTED",
            scope=application.scope.value,
        )

    ident = record(
        c.IdentifierClaim,
        claim_id="identifier_" + suffix,
        **claim_binding(app),
        identifier_kind="KRX_ISIN",
        identifier_value=isin,
        valid_from=None,
        valid_to=None,
        interval_missing_reason="NOT_SUPPLIED_BY_AUTHORITY",
    )
    klass = record(
        c.ClassClaim,
        claim_id="class_" + suffix,
        **claim_binding(class_app),
        instrument_family=c.InstrumentFamily.COMMON_EQUITY,
        registered_class_title=None,
        authority_share_kind="COMMON",
        registered_row_id=None,
        section_12_basis=None,
        missing_reason="NOT_SUPPLIED_BY_AUTHORITY",
    )
    listing = record(
        c.ListingClaim,
        claim_id="listing_" + suffix,
        **claim_binding(listing_app),
        venue="KRX",
        market="KOSPI",
        ticker="SYNTHETIC",
        listing_status="ACTIVE",
        valid_from=None,
        valid_to=None,
        interval_missing_reason="NOT_SUPPLIED_BY_AUTHORITY",
    )
    subject = record(
        c.CanonicalSubject,
        security_id=sid,
        issuer_id=binding["issuer_id"],
        founding_anchor=anchor,
        anchor_kind="KRX_ISIN",
        anchor_hash=c.security_hash(anchor),
    )
    profile = record(
        c.AuthorityProfile,
        profile_id="profile_" + suffix,
        security_id=sid,
        issuer_id=binding["issuer_id"],
        instrument_family=c.InstrumentFamily.COMMON_EQUITY,
        registered_class_title=None,
        authority_share_kind="COMMON",
        identifier_kind="KRX_ISIN",
        identifier_value=isin,
        venue="KRX",
        market="KOSPI",
        valid_from=None,
        valid_to=None,
        missing_reason="NOT_SUPPLIED_BY_AUTHORITY",
        identifier_claim_id=ident.claim_id,
        identifier_claim_hash=ident.content_hash,
        class_claim_id=klass.claim_id,
        class_claim_hash=klass.content_hash,
        listing_claim_id=listing.claim_id,
        listing_claim_hash=listing.content_hash,
    )
    bundle = record(
        c.Bundle,
        bundle_id="bundle_" + suffix,
        **binding,
        **issuer_binding,
        proposed_anchor=anchor,
        profile_hash=profile.content_hash,
        rules_version=c.RULES_VERSION,
        freshness_version="test/1",
        source_policy_set_hash=HASH,
        collision_scan_hash=HASH,
        membership_hash=c.security_hash(
            {
                "applications": sorted(
                    (x.application_id, x.content_hash) for x in (app, class_app, listing_app)
                ),
                "scopes": [],
                "providers": [],
            }
        ),
    )
    members = [
        record(
            c.BundleApplication,
            bundle_id=bundle.bundle_id,
            bundle_hash=bundle.content_hash,
            application_id=x.application_id,
            application_hash=x.content_hash,
            member_ordinal=i,
            **binding,
        )
        for i, x in enumerate(sorted((app, class_app, listing_app), key=lambda x: x.application_id))
    ]
    member = next(x for x in members if x.application_id == app.application_id)
    decision = record(
        c.Decision,
        decision_id="decision_" + suffix,
        **binding,
        **issuer_binding,
        bundle_id=bundle.bundle_id,
        bundle_hash=bundle.content_hash,
        machine_state="UNRESOLVED",
        reason_codes=("TEST_ONLY",),
        freshness_result="UNKNOWN",
        collision_result="NOT_CHECKED",
        supersedes_decision_id=predecessor,
        evaluated_at=NOW,
    )
    for value in (
        p,
        e,
        obs,
        app,
        *extra_records,
        ident,
        klass,
        listing,
        bundle,
        *members,
        decision,
        subject,
        profile,
    ):
        if not persist_subjects and isinstance(value, c.CanonicalSubject | c.AuthorityProfile):
            continue
        if isinstance(value, c.CanonicalSubject):
            existing = connection.exec_driver_sql(
                "SELECT payload_json FROM canonical_security_subjects WHERE security_id=?",
                (value.security_id,),
            ).scalar_one_or_none()
            if existing is not None:
                assert existing == c.canonical_security_bytes(value).decode()
                continue
        insert(connection, value)
    return dict(
        binding=binding,
        issuer_binding=issuer_binding,
        policy=p,
        evidence=e,
        observation=obs,
        application=app,
        identifier=ident,
        klass=klass,
        listing=listing,
        subject=subject,
        profile=profile,
        bundle=bundle,
        member=member,
        members=members,
        decision=decision,
    )


def authorization(
    connection: Connection,
    issuer: dict[str, Any],
    graph: dict[str, Any],
    suffix: str,
    disposition: str = "APPROVED",
    predecessor_event: str | None = None,
    predecessor_link: str | None = None,
    intent: str | None = None,
    successor: str | None = None,
    previous: int = 9,
    asserted: int = 10,
) -> dict[str, Any]:
    p = issuer["principal"]
    cred = issuer["credential"]
    d = graph["decision"]
    decision_binding = dict(
        **graph["binding"],
        **graph["issuer_binding"],
        decision_id=d.decision_id,
        decision_hash=d.content_hash,
        bundle_id=d.bundle_id,
        bundle_hash=d.bundle_hash,
    )
    binding = dict(
        **decision_binding,
        intent_id=intent,
        disposition=disposition,
        principal_id=p["reviewer_principal_id"],
        role="LOCAL_DATA_STEWARD",
        principal_hash=p["principal_content_hash"],
        os_owner_sid_hash=p["os_owner_sid_hash"],
        webauthn_credential_id=cred["webauthn_credential_id"],
        credential_id_fingerprint=cred["credential_id_fingerprint"],
        public_key_fingerprint=cred["public_key_fingerprint"],
        expected_head_hash=HASH,
        predecessor_approval_event_id=predecessor_event,
        predecessor_link_id=predecessor_link,
        successor_decision_id=successor,
    )
    ch = record(
        c.ApprovalChallenge,
        challenge_id="challenge_" + suffix,
        **binding,
        challenge_digest=c.security_hash(suffix),
        issued_at=NOW,
        expires_at=NOW + timedelta(minutes=5),
    )
    co = record(
        c.ChallengeConsumption,
        consumption_id="consumption_" + suffix,
        challenge_id=ch.challenge_id,
        challenge_hash=ch.content_hash,
        terminal_result="SUCCEEDED",
        safe_result_code="TEST_VERIFIED",
        consumed_at=NOW,
    )
    flags = {
        name: 1
        for name in c.AuthenticationEvent.model_fields
        if name.endswith("_verified") or name == "replay_rejected"
    }
    auth = record(
        c.AuthenticationEvent,
        authentication_event_id="authentication_" + suffix,
        **binding,
        challenge_id=ch.challenge_id,
        challenge_hash=ch.content_hash,
        consumption_id=co.consumption_id,
        consumption_hash=co.content_hash,
        consumption_result="SUCCEEDED",
        authentication_result="VERIFIED",
        counter_capability=cred["counter_capability"],
        previous_sign_count=previous,
        asserted_sign_count=asserted,
        **flags,
        rp_id="localhost",
        exact_origin="http://localhost:3000",
        authentication_policy_version="test/1",
        authenticated_at=NOW,
    )
    for value in (ch, co, auth):
        insert(connection, value)
    return dict(
        challenge=ch, consumption=co, authentication=auth, decision_binding=decision_binding
    )


def business(
    connection: Connection,
    graph: dict[str, Any],
    auth: dict[str, Any],
    suffix: str,
    predecessor_event: str | None = None,
    predecessor_link: str | None = None,
    pair: str | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    a = auth["authentication"]
    event = record(
        c.ApprovalEvent,
        approval_event_id="event_" + suffix,
        **auth["decision_binding"],
        authentication_event_id=a.authentication_event_id,
        authentication_hash=a.content_hash,
        authentication_result="VERIFIED",
        consumption_id=a.consumption_id,
        challenge_id=a.challenge_id,
        intent_id=a.intent_id,
        disposition=a.disposition,
        predecessor_approval_event_id=predecessor_event,
        pair_id=pair,
        successor_decision_id=a.successor_decision_id,
        reviewed_at=NOW,
    )
    link = record(
        c.AuthorityLink,
        link_id="link_" + suffix,
        **auth["decision_binding"],
        profile_id=graph["profile"].profile_id,
        profile_hash=graph["profile"].content_hash,
        link_state=a.disposition,
        approval_event_id=event.approval_event_id,
        approval_hash=event.content_hash,
        machine_trigger_decision_id=None,
        supersedes_link_id=predecessor_link,
        pair_id=pair,
        intent_id=a.intent_id,
    )
    if persist:
        insert(connection, event)
        insert(connection, link)
    return dict(event=event, link=link)


def head(
    connection: Connection,
    graph: dict[str, Any],
    business_rows: dict[str, Any],
    *,
    persist: bool = True,
) -> c.AuthorityLinkHead:
    link = business_rows["link"]
    value = record(
        c.AuthorityLinkHead,
        provider_id=link.provider_id,
        link_id=link.link_id,
        link_hash=link.content_hash,
        issuer_id=link.issuer_id,
        security_id=link.security_id,
        profile_id=link.profile_id,
        link_state=link.link_state,
        state_hash=HASH,
        previous_state_hash=None,
    )
    if persist:
        insert(connection, value)
    return value


def second_provider_schema_parent(context: Any, original: dict[str, Any]) -> dict[str, Any]:
    """Synthetic B parent rows for issuer-wide C guard tests, not B engine approval.

    Frozen B evaluation deliberately treats duplicate provider claims as a collision.
    This fixture exercises the accepted provider-keyed schema's representable state
    without relaxing that engine, disabling FKs or changing an existing row.
    """
    table_ids = [
        ("provider_security_identities", "provider_security_identity_id"),
        ("authority_bundles", "authority_bundle_id"),
        ("issuer_decisions", "issuer_decision_id"),
        ("issuer_approval_challenges", "issuer_approval_challenge_id"),
        ("issuer_approval_challenge_consumptions", "challenge_consumption_id"),
        ("reviewer_authentication_events", "authentication_event_id"),
        ("issuer_approval_events", "issuer_approval_event_id"),
        ("issuer_authority_links", "issuer_authority_link_id"),
        ("issuer_authority_link_heads", "provider_security_identity_id"),
        ("provider_security_master_observations", "observation_id"),
    ]
    with context.engine.begin() as connection:
        rows = [
            (
                table,
                key,
                dict(connection.exec_driver_sql(f"SELECT * FROM {table}").mappings().one()),
            )
            for table, key in table_ids
        ]
        replacements = {r[key]: "schema_second_" + key for _, key, r in rows}
        frozen_hashes = {
            "principal_content_hash",
            "credential_id_fingerprint",
            "public_key_fingerprint",
            "os_owner_sid_hash",
        }
        for _, _, value in rows:
            for field, item in value.items():
                if (
                    (field.endswith("hash") or field == "challenge_digest")
                    and field not in frozen_hashes
                    and isinstance(item, str)
                ):
                    replacements[item] = c.security_hash("second-schema-parent-" + item)

        def replace(value):
            if isinstance(value, str):
                return replacements.get(value, value)
            if isinstance(value, list):
                return [replace(x) for x in value]
            if isinstance(value, dict):
                return {k: replace(v) for k, v in value.items()}
            return value

        inserted = {}
        for table, _key, source in rows:
            data = {field: replace(value) for field, value in source.items()}
            data["payload_json"] = c.canonical_security_bytes(
                replace(c.strict_security_json(source["payload_json"]))
            ).decode()
            if table == "reviewer_authentication_events":
                data["previous_sign_count"] = 9
                data["asserted_sign_count"] = 10
            if table == "provider_security_master_observations":
                data["symbol"] = "SCHEMA_ONLY_SECOND"
            fields = list(data)
            connection.exec_driver_sql(
                f"INSERT INTO {table} ({','.join(fields)}) "
                f"VALUES ({','.join('?' for _ in fields)})",
                tuple(data[k] for k in fields),
            )
            inserted[table] = data
        assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []
    return original | {
        "link": inserted["issuer_authority_links"],
        "head": inserted["issuer_authority_link_heads"],
        "observation": inserted["provider_security_master_observations"],
    }
