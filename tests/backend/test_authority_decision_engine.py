from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Event, Thread
from typing import Any

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from authority_preadmitted_ledger import seed_preadmitted_authority_snapshot
from authority_test_helpers import fixture_source_policy
from toss_dashboard_api.authority_source_registry import (
    KR_IROS_COMPLETE_POLICY,
    OPENDART_COMPANY_OVERVIEW_POLICY,
    OPENDART_CORP_CODE_POLICY,
    PRODUCTION_AUTHORITY_SOURCE_POLICIES,
    SEC_ACCEPTED_FILING_POLICY,
    SEC_LOGIN_PROVENANCE_POLICY,
    US_STATE_REGISTRY_DE_POLICY,
)
from toss_dashboard_api.contracts.authority import (
    AuthorityAccessDisposition,
    AuthorityClassification,
    AuthorityEvidence,
    AuthorityEvidenceApplicationStatus,
    AuthorityEvidenceKind,
    AuthorityEvidenceRelationType,
    AuthorityFreshnessResult,
    AuthorityIdentifierKind,
    AuthorityIngestionMode,
    AuthorityLicenseDisposition,
    AuthorityOriginDataMode,
    AuthorityRetrievalStatus,
    AuthorityScope,
    AuthorityScopeRoleWeight,
    AuthoritySubjectRole,
    AuthorityTimeMissingReason,
    AuthorityWeight,
    IssuerMachineDecisionState,
    authority_sha256,
    build_authority_evidence,
    build_authority_evidence_application,
    build_authority_evidence_observation,
    build_authority_evidence_relation,
    build_authority_identifier_claim,
    build_authority_source_policy,
    build_issuer_decision,
    proposed_issuer_anchor,
    proposed_issuer_id,
)
from toss_dashboard_api.contracts.authority_decision import (
    AuthorityBridgeStatus,
    IssuerAuthorityEvaluationRequest,
    build_issuer_authority_evaluation_request,
)
from toss_dashboard_api.contracts.base import normalized_hash
from toss_dashboard_api.contracts.enums import (
    Jurisdiction,
    MappingStatus,
    Market,
    MissingReason,
    ProviderIdentityState,
    ProviderReconciliationOutcome,
    ProviderSecurityMasterState,
    ProviderSecurityType,
    ProviderSystem,
)
from toss_dashboard_api.contracts.issuer import Issuer
from toss_dashboard_api.contracts.provider_identity import (
    PROVIDER_IDENTITY_CONTRACT_VERSION,
    ProviderSecurityIdentity,
)
from toss_dashboard_api.contracts.provider_security_master import (
    build_security_master_observation,
)
from toss_dashboard_api.domain.issuer_authority import (
    IssuerAuthorityDecisionEngine,
    IssuerAuthorityDecisionEngineError,
)
from toss_dashboard_api.repositories.authority import (
    AuthorityLedgerConflict,
    AuthorityProductionAdmissionUnavailable,
    AuthorityReviewReadyEngineNotImplemented,
    SQLiteAuthorityLedgerRepository,
)
from toss_dashboard_api.storage.database import session_factory
from toss_dashboard_api.storage.models import (
    AuthorityBundleRow,
    AuthorityEvidenceRelationRow,
    AuthorityIdentifierClaimRow,
    CanonicalRequestRow,
    IssuerDecisionRow,
    IssuerRow,
    ProviderIdentityMappingRow,
    ProviderRawManifestRow,
    ProviderSecurityIdentityRow,
    ProviderSecurityMasterObservationRow,
    ProviderSourceVersionRow,
    SecurityRow,
)

EVALUATED_AT = datetime(2026, 8, 27, 12, 0, 0, tzinfo=UTC)
CURRENT_FETCHED_AT = EVALUATED_AT - timedelta(hours=1)
HISTORICAL_FETCHED_AT = EVALUATED_AT - timedelta(days=120)
STALE_FETCHED_AT = EVALUATED_AT - timedelta(hours=25)
KR_CORP_CODE = "00126380"
KR_JURIR_NO = "1101110000000"
KR_SYMBOL = "005930"
KR_LEGAL_NAME = "Exact Korean Corporation"
US_CIK = "0000789019"
US_ACCESSION = "0000789019-26-000001"
US_SECOND_ACCESSION = "0000789019-26-000003"
US_THIRD_ACCESSION = "0000789019-26-000004"
US_LATEST_ACCESSION = "0000789019-26-000002"
US_STATE_ENTITY_NUMBER = "1234567"
US_SYMBOL = "MSFT"
US_LEGAL_NAME = "Exact U.S. Corporation"


@dataclass
class _TestClock:
    value: datetime

    def __call__(self) -> datetime:
        return self.value


@dataclass(frozen=True)
class _Harness:
    sessions: sessionmaker[Session]
    repository: SQLiteAuthorityLedgerRepository
    engine: IssuerAuthorityDecisionEngine
    clock: _TestClock
    provider_id: str
    provider_observation_id: str
    evidence: dict[str, AuthorityEvidence]


def _seed_exact_provider(
    sessions: sessionmaker[Session],
    *,
    label: str,
    market: Market,
    symbol: str,
    name: str,
) -> tuple[str, str]:
    anchor_hash = authority_sha256({"exact_provider_authority_subject": label})
    provider_id = "tpsi_" + anchor_hash.removeprefix("sha256:")
    request_id = f"canonical_request_authority_{label}"
    raw_id = f"raw_response_authority_{label}"
    source_id = f"provider_source_authority_{label}"
    identity = ProviderSecurityIdentity(
        provider_security_identity_id=provider_id,
        provider=ProviderSystem.TOSS_OPEN_API,
        market=market,
        allocation_anchor_hash=anchor_hash,
        identity_state=ProviderIdentityState.ACTIVE,
        mapping_status=MappingStatus.UNRESOLVED,
        first_source_version_id=source_id,
        latest_source_version_id=source_id,
        provider_contract_version=PROVIDER_IDENTITY_CONTRACT_VERSION,
    )
    observation = build_security_master_observation(
        source_version_id=source_id,
        normalized_record_id=None,
        provider_security_identity_id=provider_id,
        provider=ProviderSystem.TOSS_OPEN_API,
        market=market,
        symbol=symbol,
        name=name,
        security_type=ProviderSecurityType.STOCK,
        is_common_share=True,
        isin=None,
        staging_state=ProviderSecurityMasterState.ELIGIBLE_FOR_MAPPING,
        reconciliation_outcome=ProviderReconciliationOutcome.IDENTITY_ALLOCATED,
        identity_state_after=ProviderIdentityState.ACTIVE,
        eligible_for_mapping=True,
        collision_identity_ids=(),
        reason_codes=("EXACT_CP3_C1_LINEAGE",),
    )
    raw_hash = authority_sha256({"provider_source": label})
    with sessions.begin() as session:
        session.add(
            CanonicalRequestRow(
                canonical_request_id=request_id,
                provider=ProviderSystem.TOSS_OPEN_API.value,
                method="GET",
                path_template="/api/v1/stocks",
                canonical_query_json="{}",
                canonical_query_hash=authority_sha256({}),
                provider_contract_version="toss-provider/0.1.0",
                payload_json="{}",
            )
        )
        session.add(
            ProviderRawManifestRow(
                raw_response_id=raw_id,
                canonical_request_id=request_id,
                http_status=200,
                raw_content_hash=raw_hash,
                raw_storage_ref=f"raw:sha256/{label}",
                fetched_at="2026-08-27T10:00:00Z",
                response_metadata_json="{}",
                provider_contract_version="toss-provider/0.1.0",
                payload_json="{}",
            )
        )
        session.add(
            ProviderSourceVersionRow(
                source_version_id=source_id,
                canonical_request_id=request_id,
                raw_response_id=raw_id,
                dataset="STOCK_DETAIL",
                http_status=200,
                raw_content_hash=raw_hash,
                provider_contract_version="toss-provider/0.1.0",
                revision_status="ORIGINAL",
                supersedes_id=None,
                normalized_content_hash=authority_sha256({"provider": label}),
                payload_json="{}",
            )
        )
        session.flush()
        session.add(
            ProviderSecurityIdentityRow(
                provider_security_identity_id=provider_id,
                provider=identity.provider.value,
                market=identity.market.value,
                allocation_anchor_hash=identity.allocation_anchor_hash,
                identity_state=identity.identity_state.value,
                mapping_status=identity.mapping_status.value,
                first_source_version_id=identity.first_source_version_id,
                latest_source_version_id=identity.latest_source_version_id,
                provider_contract_version=identity.provider_contract_version,
                payload_json=identity.model_dump_json(),
            )
        )
        session.flush()
        session.add(
            ProviderSecurityMasterObservationRow(
                observation_id=observation.observation_id,
                source_version_id=observation.source_version_id,
                normalized_record_id=observation.normalized_record_id,
                provider_security_identity_id=observation.provider_security_identity_id,
                provider=observation.provider.value,
                market=observation.market.value,
                symbol=observation.symbol,
                staging_state=observation.staging_state.value,
                reconciliation_outcome=observation.reconciliation_outcome.value,
                eligible_for_mapping=int(observation.eligible_for_mapping),
                provider_contract_version=observation.provider_contract_version,
                payload_json=observation.model_dump_json(),
            )
        )
    return provider_id, observation.observation_id


def _missing_times() -> dict[str, AuthorityTimeMissingReason]:
    return {
        "authority_published_at": AuthorityTimeMissingReason.NOT_SUPPLIED_BY_AUTHORITY,
        "authority_accepted_at": AuthorityTimeMissingReason.NOT_SUPPLIED_BY_AUTHORITY,
        "authority_as_of_date": AuthorityTimeMissingReason.NOT_SUPPLIED_BY_AUTHORITY,
        "authority_effective_at": AuthorityTimeMissingReason.NOT_SUPPLIED_BY_AUTHORITY,
        "authority_effective_date": AuthorityTimeMissingReason.NOT_SUPPLIED_BY_AUTHORITY,
    }


def _evidence(
    *,
    policy,
    document_kind: str,
    document_reference: str,
    document_group: str,
    scope: AuthorityScope,
    role: AuthoritySubjectRole,
    claim_field: str,
    value: Any,
    raw_value: Any | None = None,
    evidence_kind: AuthorityEvidenceKind = AuthorityEvidenceKind.ASSERTION,
    authority_accepted_at: datetime | None = None,
) -> AuthorityEvidence:
    missing_times = _missing_times()
    if authority_accepted_at is not None:
        missing_times.pop("authority_accepted_at")
    return build_authority_evidence(
        authority_source_policy_id=policy.authority_source_policy_id,
        authority_source_identifier=policy.source_namespace,
        authority_classification=policy.authority_classification,
        authority_source_locator=policy.credential_free_locator_roots[0] + document_group,
        authority_document_reference=document_reference,
        source_document_kind=document_kind,
        authority_external_key=document_reference,
        raw_content_hash=authority_sha256({"authority_document": document_group}),
        parser_contract_version=policy.admitted_parser_contract_versions[0],
        evidence_kind=evidence_kind,
        authority_scope=scope,
        subject_role=role,
        policy_maximum_issuer_authority_weight=policy.maximum_weight_for(scope, role),
        claim_field=claim_field,
        raw_claim_value=value if raw_value is None else raw_value,
        normalized_claim_value=value,
        authority_published_at=None,
        authority_accepted_at=authority_accepted_at,
        authority_as_of_date=None,
        authority_effective_at=None,
        authority_effective_date=None,
        authority_time_missing_reasons=missing_times,
        access_disposition=policy.required_access_disposition,
        license_disposition=policy.required_license_disposition,
        origin_data_mode=AuthorityOriginDataMode.PRODUCTION_AUTHORITY,
        origin_adapter_class=policy.admitted_adapter_contract_versions[0],
        origin_source_system=policy.source_namespace,
        lineage_tainted=False,
        lineage_ancestor_tainted=False,
        lineage_ancestor_hashes=(),
    )


def _persist_evidence(
    repository: SQLiteAuthorityLedgerRepository,
    evidence: AuthorityEvidence,
    *,
    fetched_at: datetime,
    retrieval_status: AuthorityRetrievalStatus = AuthorityRetrievalStatus.SUCCEEDED,
) -> None:
    observation = build_authority_evidence_observation(
        evidence_id=evidence.evidence_id,
        fetched_at=fetched_at,
        raw_content_hash=evidence.raw_content_hash,
        authority_source_locator=evidence.authority_source_locator,
        authority_document_reference=evidence.authority_document_reference,
        retrieval_status=retrieval_status,
        secret_free_retrieval_fingerprint=authority_sha256(
            {"safe_retrieval": evidence.evidence_id, "at": fetched_at}
        ),
        safe_status_code=(
            "OK" if retrieval_status == AuthorityRetrievalStatus.SUCCEEDED else "UNAVAILABLE"
        ),
    )
    seed_preadmitted_authority_snapshot(
        repository._sessions,
        evidence=(evidence,),
        observations=(observation,),
    )


def _repository_and_engine(
    database_context,
) -> tuple[
    sessionmaker[Session],
    SQLiteAuthorityLedgerRepository,
    IssuerAuthorityDecisionEngine,
    _TestClock,
]:
    sessions = session_factory(database_context.engine)
    repository = SQLiteAuthorityLedgerRepository(sessions)
    clock = _TestClock(EVALUATED_AT)
    return sessions, repository, IssuerAuthorityDecisionEngine(sessions, clock=clock), clock


def _kr_harness(
    database_context,
    *,
    label: str = "kr_primary",
    include_iros: bool = True,
    iros_verified: bool = True,
    iros_entity_kind: str = "DOMESTIC_CORPORATION",
    overview_jurir: str = KR_JURIR_NO,
    iros_jurir: str = KR_JURIR_NO,
    overview_symbol: str = KR_SYMBOL,
    current_fetched_at: datetime = CURRENT_FETCHED_AT,
    current_status: AuthorityRetrievalStatus = AuthorityRetrievalStatus.SUCCEEDED,
    overview_mode: str = "EXACT",
    corp_code: str = KR_CORP_CODE,
    opendart_legal_name: str = KR_LEGAL_NAME,
    iros_legal_name: str = KR_LEGAL_NAME,
) -> _Harness:
    sessions, repository, engine, clock = _repository_and_engine(database_context)
    provider_id, observation_id = _seed_exact_provider(
        sessions,
        label=label,
        market=Market.KR,
        symbol=KR_SYMBOL,
        name="Korean authority subject",
    )
    for policy in (
        OPENDART_CORP_CODE_POLICY,
        OPENDART_COMPANY_OVERVIEW_POLICY,
        KR_IROS_COMPLETE_POLICY,
    ):
        seed_preadmitted_authority_snapshot(sessions, policies=(policy,))
    evidence: dict[str, AuthorityEvidence] = {}
    evidence["corp"] = _evidence(
        policy=OPENDART_CORP_CODE_POLICY,
        document_kind="CORP_CODE_XML_V1",
        document_reference=f"corp-code:{corp_code}",
        document_group=f"corp-code-{corp_code}",
        scope=AuthorityScope.ISSUER_REGULATORY_ID,
        role=AuthoritySubjectRole.DART_DISCLOSURE_FILER,
        claim_field="corp_list.corp.corp_code",
        value=corp_code,
    )
    _persist_evidence(repository, evidence["corp"], fetched_at=HISTORICAL_FETCHED_AT)
    if overview_mode == "EXACT":
        evidence["overview"] = _evidence(
            policy=OPENDART_COMPANY_OVERVIEW_POLICY,
            document_kind="COMPANY_OVERVIEW_JSON_V1",
            document_reference=f"company-overview:{corp_code}",
            document_group=f"company-overview-{corp_code}",
            scope=AuthorityScope.LEGAL_ENTITY_BRIDGE,
            role=AuthoritySubjectRole.DART_DISCLOSURE_FILER,
            claim_field="company.identity_bridge",
            value={
                "corp_code": corp_code,
                "jurir_no": overview_jurir,
                "stock_code": overview_symbol,
            },
        )
    elif overview_mode == "NAME_ONLY":
        evidence["overview"] = _evidence(
            policy=OPENDART_COMPANY_OVERVIEW_POLICY,
            document_kind="COMPANY_OVERVIEW_JSON_V1",
            document_reference=f"company-overview:{corp_code}",
            document_group=f"company-overview-{corp_code}",
            scope=AuthorityScope.LEGAL_NAME,
            role=AuthoritySubjectRole.DART_DISCLOSURE_FILER,
            claim_field="company.corp_name",
            value="Korean authority subject",
        )
    else:
        evidence["overview"] = _evidence(
            policy=OPENDART_COMPANY_OVERVIEW_POLICY,
            document_kind="COMPANY_OVERVIEW_JSON_V1",
            document_reference=f"company-overview:{corp_code}",
            document_group=f"company-overview-{corp_code}",
            scope=AuthorityScope.LEGAL_ENTITY_BRIDGE,
            role=AuthoritySubjectRole.DART_DISCLOSURE_FILER,
            claim_field="company.stock_code",
            value=overview_symbol,
        )
    _persist_evidence(
        repository,
        evidence["overview"],
        fetched_at=current_fetched_at,
        retrieval_status=current_status,
    )
    if overview_mode != "NAME_ONLY":
        evidence["overview_name"] = _evidence(
            policy=OPENDART_COMPANY_OVERVIEW_POLICY,
            document_kind="COMPANY_OVERVIEW_JSON_V1",
            document_reference=f"company-overview:{corp_code}",
            document_group=f"company-overview-{corp_code}",
            scope=AuthorityScope.LEGAL_NAME,
            role=AuthoritySubjectRole.DART_DISCLOSURE_FILER,
            claim_field="company.corp_name",
            value=opendart_legal_name,
        )
        _persist_evidence(
            repository,
            evidence["overview_name"],
            fetched_at=current_fetched_at,
            retrieval_status=current_status,
        )
    if include_iros:
        verification_reference = f"iros-verified-original:{iros_jurir}"
        evidence["iros_jurisdiction"] = _evidence(
            policy=KR_IROS_COMPLETE_POLICY,
            document_kind="VERIFIED_CORPORATE_REGISTRY_EXTRACT_V1",
            document_reference=verification_reference,
            document_group=f"iros-record-{iros_jurir}",
            scope=AuthorityScope.LEGAL_JURISDICTION,
            role=AuthoritySubjectRole.KOREAN_REGISTERED_LEGAL_ENTITY,
            claim_field="registry.legal_entity_status",
            value={
                "corporate_registration_reference": iros_jurir,
                "entity_kind": iros_entity_kind,
                "jurisdiction": "KR",
                "verification_reference": (
                    verification_reference if iros_verified else "unverified-copy"
                ),
            },
        )
        evidence["iros_bridge"] = _evidence(
            policy=KR_IROS_COMPLETE_POLICY,
            document_kind="VERIFIED_CORPORATE_REGISTRY_EXTRACT_V1",
            document_reference=verification_reference,
            document_group=f"iros-record-{iros_jurir}",
            scope=AuthorityScope.LEGAL_ENTITY_BRIDGE,
            role=AuthoritySubjectRole.KOREAN_REGISTERED_LEGAL_ENTITY,
            claim_field="registry.corporate_registration_reference",
            value=iros_jurir,
        )
        evidence["iros_name"] = _evidence(
            policy=KR_IROS_COMPLETE_POLICY,
            document_kind="VERIFIED_CORPORATE_REGISTRY_EXTRACT_V1",
            document_reference=verification_reference,
            document_group=f"iros-record-{iros_jurir}",
            scope=AuthorityScope.LEGAL_NAME,
            role=AuthoritySubjectRole.KOREAN_REGISTERED_LEGAL_ENTITY,
            claim_field="registry.legal_name",
            value=iros_legal_name,
        )
        for key in ("iros_jurisdiction", "iros_bridge", "iros_name"):
            _persist_evidence(
                repository,
                evidence[key],
                fetched_at=current_fetched_at,
                retrieval_status=current_status,
            )
    return _Harness(
        sessions=sessions,
        repository=repository,
        engine=engine,
        clock=clock,
        provider_id=provider_id,
        provider_observation_id=observation_id,
        evidence=evidence,
    )


def _us_harness(
    database_context,
    *,
    label: str = "us_primary",
    include_state: bool = True,
    state_namespace_exact: bool = True,
    state_record_kind: str = "DOMESTIC_FORMATION",
    state_value: str = "DE",
    provider_symbol: str = US_SYMBOL,
    current_fetched_at: datetime = CURRENT_FETCHED_AT,
    current_status: AuthorityRetrievalStatus = AuthorityRetrievalStatus.SUCCEEDED,
    include_latest_status: bool = True,
    sec_bridge_mode: str = "EXACT",
    cik: str = US_CIK,
    sec_legal_name: str = US_LEGAL_NAME,
    state_legal_name: str = US_LEGAL_NAME,
    accession: str = US_ACCESSION,
    filing_accepted_at: datetime | None = None,
) -> _Harness:
    sessions, repository, engine, clock = _repository_and_engine(database_context)
    provider_id, observation_id = _seed_exact_provider(
        sessions,
        label=label,
        market=Market.US,
        symbol=US_SYMBOL,
        name="U.S. authority subject",
    )
    for policy in (SEC_ACCEPTED_FILING_POLICY, US_STATE_REGISTRY_DE_POLICY):
        seed_preadmitted_authority_snapshot(sessions, policies=(policy,))
    evidence: dict[str, AuthorityEvidence] = {}
    filing_group = f"sec-filing-{accession}"
    evidence["cik"] = _evidence(
        policy=SEC_ACCEPTED_FILING_POLICY,
        document_kind="SEC_ACCEPTED_ISSUER_FILING_JSON_V1",
        document_reference=accession,
        document_group=filing_group,
        scope=AuthorityScope.ISSUER_REGULATORY_ID,
        role=AuthoritySubjectRole.SEC_REGISTRANT,
        claim_field="filing.registrant_cik",
        value=cik,
        authority_accepted_at=filing_accepted_at,
    )
    evidence["role"] = _evidence(
        policy=SEC_ACCEPTED_FILING_POLICY,
        document_kind="SEC_ACCEPTED_ISSUER_FILING_JSON_V1",
        document_reference=accession,
        document_group=filing_group,
        scope=AuthorityScope.REGISTRANT_ROLE,
        role=AuthoritySubjectRole.SEC_REGISTRANT,
        claim_field="filing.registrant_role",
        value={
            "accepted_accession": accession,
            "registrant_cik": cik,
            "role": "ISSUER_REGISTRANT",
        },
        authority_accepted_at=filing_accepted_at,
    )
    if sec_bridge_mode == "EXACT":
        bridge_value: Any = {
            "accepted_accession": accession,
            "formation_state": state_value,
            "provider_symbol": provider_symbol,
            "registrant_cik": cik,
            "state_entity_number": US_STATE_ENTITY_NUMBER,
        }
        bridge_field = "filing.legal_entity_bridge"
    elif sec_bridge_mode == "NAME_ONLY":
        bridge_value = "U.S. authority subject"
        bridge_field = "filing.legal_name"
    else:
        bridge_value = provider_symbol
        bridge_field = "filing.ticker"
    evidence["bridge"] = _evidence(
        policy=SEC_ACCEPTED_FILING_POLICY,
        document_kind="SEC_ACCEPTED_ISSUER_FILING_JSON_V1",
        document_reference=accession,
        document_group=filing_group,
        scope=(
            AuthorityScope.LEGAL_ENTITY_BRIDGE
            if sec_bridge_mode != "NAME_ONLY"
            else AuthorityScope.LEGAL_NAME
        ),
        role=AuthoritySubjectRole.SEC_REGISTRANT,
        claim_field=bridge_field,
        value=bridge_value,
        authority_accepted_at=filing_accepted_at,
    )
    if sec_bridge_mode != "NAME_ONLY":
        evidence["sec_name"] = _evidence(
            policy=SEC_ACCEPTED_FILING_POLICY,
            document_kind="SEC_ACCEPTED_ISSUER_FILING_JSON_V1",
            document_reference=accession,
            document_group=filing_group,
            scope=AuthorityScope.LEGAL_NAME,
            role=AuthoritySubjectRole.SEC_REGISTRANT,
            claim_field="filing.legal_name",
            value=sec_legal_name,
            authority_accepted_at=filing_accepted_at,
        )
    for key in ("cik", "role", "bridge", "sec_name"):
        if key not in evidence:
            continue
        _persist_evidence(repository, evidence[key], fetched_at=HISTORICAL_FETCHED_AT)
    if include_latest_status:
        evidence["latest"] = _evidence(
            policy=SEC_ACCEPTED_FILING_POLICY,
            document_kind="SEC_REGISTRANT_LATEST_STATUS_JSON_V1",
            document_reference=US_LATEST_ACCESSION,
            document_group=f"sec-latest-{cik}",
            scope=AuthorityScope.REGISTRANT_ROLE,
            role=AuthoritySubjectRole.SEC_REGISTRANT,
            claim_field="registrant.latest_filing_status",
            value={
                "latest_accession": US_LATEST_ACCESSION,
                "registrant_cik": cik,
                "status": "CURRENT",
            },
        )
        _persist_evidence(
            repository,
            evidence["latest"],
            fetched_at=current_fetched_at,
            retrieval_status=current_status,
        )
    if include_state and state_namespace_exact:
        verification_reference = f"de-verified-entity:{US_STATE_ENTITY_NUMBER}"
        evidence["state"] = _evidence(
            policy=US_STATE_REGISTRY_DE_POLICY,
            document_kind="VERIFIED_DOMESTIC_ENTITY_RECORD_V1",
            document_reference=verification_reference,
            document_group=f"de-entity-{US_STATE_ENTITY_NUMBER}",
            scope=AuthorityScope.LEGAL_JURISDICTION,
            role=AuthoritySubjectRole.US_STATE_REGISTERED_LEGAL_ENTITY,
            claim_field="registry.legal_entity_status",
            value={
                "formation_state": state_value,
                "jurisdiction": "US",
                "record_kind": state_record_kind,
                "state_entity_number": US_STATE_ENTITY_NUMBER,
                "status": "ACTIVE",
                "verification_reference": verification_reference,
            },
        )
        evidence["state_name"] = _evidence(
            policy=US_STATE_REGISTRY_DE_POLICY,
            document_kind="VERIFIED_DOMESTIC_ENTITY_RECORD_V1",
            document_reference=verification_reference,
            document_group=f"de-entity-{US_STATE_ENTITY_NUMBER}",
            scope=AuthorityScope.LEGAL_NAME,
            role=AuthoritySubjectRole.US_STATE_REGISTERED_LEGAL_ENTITY,
            claim_field="registry.legal_name",
            value=state_legal_name,
        )
        for key in ("state", "state_name"):
            _persist_evidence(
                repository,
                evidence[key],
                fetched_at=current_fetched_at,
                retrieval_status=current_status,
            )
    return _Harness(
        sessions=sessions,
        repository=repository,
        engine=engine,
        clock=clock,
        provider_id=provider_id,
        provider_observation_id=observation_id,
        evidence=evidence,
    )


def _append_us_accepted_filing(
    harness: _Harness,
    *,
    accession: str,
    formation_state: str = "DE",
    state_entity_number: str = US_STATE_ENTITY_NUMBER,
    provider_symbol: str = US_SYMBOL,
    legal_name: str = US_LEGAL_NAME,
    accepted_at: datetime | None = None,
    insertion_order: tuple[str, ...] = ("cik", "role", "bridge", "name"),
) -> dict[str, AuthorityEvidence]:
    document_group = f"sec-filing-{accession}"
    evidence = {
        "cik": _evidence(
            policy=SEC_ACCEPTED_FILING_POLICY,
            document_kind="SEC_ACCEPTED_ISSUER_FILING_JSON_V1",
            document_reference=accession,
            document_group=document_group,
            scope=AuthorityScope.ISSUER_REGULATORY_ID,
            role=AuthoritySubjectRole.SEC_REGISTRANT,
            claim_field="filing.registrant_cik",
            value=US_CIK,
            authority_accepted_at=accepted_at,
        ),
        "role": _evidence(
            policy=SEC_ACCEPTED_FILING_POLICY,
            document_kind="SEC_ACCEPTED_ISSUER_FILING_JSON_V1",
            document_reference=accession,
            document_group=document_group,
            scope=AuthorityScope.REGISTRANT_ROLE,
            role=AuthoritySubjectRole.SEC_REGISTRANT,
            claim_field="filing.registrant_role",
            value={
                "accepted_accession": accession,
                "registrant_cik": US_CIK,
                "role": "ISSUER_REGISTRANT",
            },
            authority_accepted_at=accepted_at,
        ),
        "bridge": _evidence(
            policy=SEC_ACCEPTED_FILING_POLICY,
            document_kind="SEC_ACCEPTED_ISSUER_FILING_JSON_V1",
            document_reference=accession,
            document_group=document_group,
            scope=AuthorityScope.LEGAL_ENTITY_BRIDGE,
            role=AuthoritySubjectRole.SEC_REGISTRANT,
            claim_field="filing.legal_entity_bridge",
            value={
                "accepted_accession": accession,
                "formation_state": formation_state,
                "provider_symbol": provider_symbol,
                "registrant_cik": US_CIK,
                "state_entity_number": state_entity_number,
            },
            authority_accepted_at=accepted_at,
        ),
        "name": _evidence(
            policy=SEC_ACCEPTED_FILING_POLICY,
            document_kind="SEC_ACCEPTED_ISSUER_FILING_JSON_V1",
            document_reference=accession,
            document_group=document_group,
            scope=AuthorityScope.LEGAL_NAME,
            role=AuthoritySubjectRole.SEC_REGISTRANT,
            claim_field="filing.legal_name",
            value=legal_name,
            authority_accepted_at=accepted_at,
        ),
    }
    assert set(insertion_order) == set(evidence)
    for key in insertion_order:
        _persist_evidence(
            harness.repository,
            evidence[key],
            fetched_at=HISTORICAL_FETCHED_AT,
        )
    return evidence


def _request(
    harness: _Harness,
    *,
    jurisdiction: Jurisdiction,
    identifier_kind: AuthorityIdentifierKind,
    identifier_value: str,
    evidence_ids: tuple[str, ...] | None = None,
):
    return build_issuer_authority_evaluation_request(
        provider_security_identity_id=harness.provider_id,
        provider_observation_ids=(harness.provider_observation_id,),
        candidate_jurisdiction=jurisdiction,
        candidate_identifier_kind=identifier_kind,
        candidate_identifier_value=identifier_value,
        evidence_ids=(
            tuple(item.evidence_id for item in harness.evidence.values())
            if evidence_ids is None
            else evidence_ids
        ),
    )


def _kr_request(harness: _Harness, **kwargs):
    return _request(
        harness,
        jurisdiction=Jurisdiction.KR,
        identifier_kind=AuthorityIdentifierKind.DART_CORP_CODE,
        identifier_value=kwargs.pop("identifier_value", KR_CORP_CODE),
        **kwargs,
    )


def _us_request(harness: _Harness, **kwargs):
    return _request(
        harness,
        jurisdiction=Jurisdiction.US,
        identifier_kind=AuthorityIdentifierKind.SEC_REGISTRANT_CIK,
        identifier_value=kwargs.pop("identifier_value", US_CIK),
        **kwargs,
    )


def _zero_snapshot(sessions: sessionmaker[Session]) -> dict[str, Any]:
    with sessions() as session:
        return {
            "issuers": int(session.scalar(select(func.count()).select_from(IssuerRow)) or 0),
            "securities": int(session.scalar(select(func.count()).select_from(SecurityRow)) or 0),
            "verified": int(
                session.scalar(
                    select(func.count())
                    .select_from(ProviderIdentityMappingRow)
                    .where(ProviderIdentityMappingRow.mapping_status == "VERIFIED")
                )
                or 0
            ),
            "anchors": tuple(
                session.execute(
                    select(
                        ProviderSecurityIdentityRow.provider_security_identity_id,
                        ProviderSecurityIdentityRow.allocation_anchor_hash,
                    ).order_by(ProviderSecurityIdentityRow.provider_security_identity_id)
                ).all()
            ),
        }


def _canonical_issuer(
    *,
    jurisdiction: Jurisdiction,
    identifier_value: str,
) -> Issuer:
    identifier_kind = (
        AuthorityIdentifierKind.DART_CORP_CODE
        if jurisdiction == Jurisdiction.KR
        else AuthorityIdentifierKind.SEC_REGISTRANT_CIK
    )
    values: dict[str, Any] = {
        "contract_version": "0.1.0",
        "missing_reasons": (
            {"cik": MissingReason.NOT_APPLICABLE}
            if jurisdiction == Jurisdiction.KR
            else {"corp_code": MissingReason.NOT_APPLICABLE}
        ),
        "issuer_id": proposed_issuer_id(
            proposed_issuer_anchor(jurisdiction, identifier_kind, identifier_value)
        ),
        "legal_name": "Exact canonical authority subject",
        "display_name": "Exact canonical authority subject",
        "jurisdiction": jurisdiction,
        "corp_code": identifier_value if jurisdiction == Jurisdiction.KR else None,
        "cik": identifier_value if jurisdiction == Jurisdiction.US else None,
    }
    values["normalized_content_hash"] = normalized_hash(values)
    return Issuer.model_validate(values)


def _insert_canonical_issuer(
    sessions: sessionmaker[Session],
    issuer: Issuer,
) -> None:
    with sessions.begin() as session:
        session.add(
            IssuerRow(
                issuer_id=issuer.issuer_id,
                jurisdiction=issuer.jurisdiction.value,
                corp_code=issuer.corp_code,
                cik=issuer.cik,
                normalized_content_hash=issuer.normalized_content_hash,
                payload_json=issuer.model_dump_json(),
            )
        )


def _seed_decisive_legal_name_history(
    harness: _Harness,
    *,
    current: AuthorityEvidence,
    policy,
    document_kind: str,
    document_reference: str,
    document_group: str,
    role: AuthoritySubjectRole,
    claim_field: str,
    former_name: str,
    kr_jurir_no: str = KR_JURIR_NO,
    us_formation_state: str = "DE",
    us_state_entity_number: str = US_STATE_ENTITY_NUMBER,
    relation_type: AuthorityEvidenceRelationType = AuthorityEvidenceRelationType.SUPERSEDES,
    relation_order: tuple[str, ...] = ("subject", "name"),
) -> AuthorityEvidence:
    former = _evidence(
        policy=policy,
        document_kind=document_kind,
        document_reference=document_reference,
        document_group=document_group,
        scope=AuthorityScope.LEGAL_NAME,
        role=role,
        claim_field=claim_field,
        value=former_name,
    )
    historical_facts = [former]
    subject_relations = []
    if policy == KR_IROS_COMPLETE_POLICY:
        former_jurisdiction = _evidence(
            policy=policy,
            document_kind=document_kind,
            document_reference=document_reference,
            document_group=document_group,
            scope=AuthorityScope.LEGAL_JURISDICTION,
            role=role,
            claim_field="registry.legal_entity_status",
            value={
                "corporate_registration_reference": kr_jurir_no,
                "entity_kind": "DOMESTIC_CORPORATION",
                "jurisdiction": "KR",
                "verification_reference": document_reference,
            },
        )
        former_bridge = _evidence(
            policy=policy,
            document_kind=document_kind,
            document_reference=document_reference,
            document_group=document_group,
            scope=AuthorityScope.LEGAL_ENTITY_BRIDGE,
            role=role,
            claim_field="registry.corporate_registration_reference",
            value=kr_jurir_no,
        )
        historical_facts.extend((former_jurisdiction, former_bridge))
        subject_relations.extend(
            (
                build_authority_evidence_relation(
                    predecessor_evidence_id=former_jurisdiction.evidence_id,
                    successor_evidence_id=harness.evidence["iros_jurisdiction"].evidence_id,
                    relation_type=relation_type,
                    recorded_at=EVALUATED_AT,
                    authority_effective_missing_reason=(
                        AuthorityTimeMissingReason.NOT_SUPPLIED_BY_AUTHORITY
                    ),
                ),
                build_authority_evidence_relation(
                    predecessor_evidence_id=former_bridge.evidence_id,
                    successor_evidence_id=harness.evidence["iros_bridge"].evidence_id,
                    relation_type=relation_type,
                    recorded_at=EVALUATED_AT,
                    authority_effective_missing_reason=(
                        AuthorityTimeMissingReason.NOT_SUPPLIED_BY_AUTHORITY
                    ),
                ),
            )
        )
    elif policy == US_STATE_REGISTRY_DE_POLICY:
        former_jurisdiction = _evidence(
            policy=policy,
            document_kind=document_kind,
            document_reference=document_reference,
            document_group=document_group,
            scope=AuthorityScope.LEGAL_JURISDICTION,
            role=role,
            claim_field="registry.legal_entity_status",
            value={
                "formation_state": us_formation_state,
                "jurisdiction": "US",
                "record_kind": "DOMESTIC_FORMATION",
                "state_entity_number": us_state_entity_number,
                "status": "ACTIVE",
                "verification_reference": document_reference,
            },
        )
        historical_facts.append(former_jurisdiction)
        subject_relations.append(
            build_authority_evidence_relation(
                predecessor_evidence_id=former_jurisdiction.evidence_id,
                successor_evidence_id=harness.evidence["state"].evidence_id,
                relation_type=relation_type,
                recorded_at=EVALUATED_AT,
                authority_effective_missing_reason=(
                    AuthorityTimeMissingReason.NOT_SUPPLIED_BY_AUTHORITY
                ),
            )
        )
    else:
        raise AssertionError("legal-name history helper requires a decisive registry policy")
    for item in historical_facts:
        _persist_evidence(harness.repository, item, fetched_at=HISTORICAL_FETCHED_AT)
    name_relation = build_authority_evidence_relation(
        predecessor_evidence_id=former.evidence_id,
        successor_evidence_id=current.evidence_id,
        relation_type=relation_type,
        recorded_at=EVALUATED_AT,
        authority_effective_missing_reason=(AuthorityTimeMissingReason.NOT_SUPPLIED_BY_AUTHORITY),
    )
    relation_groups = {"subject": tuple(subject_relations), "name": (name_relation,)}
    assert set(relation_order) == set(relation_groups)
    relations = tuple(relation for group in relation_order for relation in relation_groups[group])
    seed_preadmitted_authority_snapshot(harness.sessions, relations=relations)
    return former


def test_server_owned_registry_is_exact_and_has_no_wildcard_namespace() -> None:
    namespaces = {policy.source_namespace for policy in PRODUCTION_AUTHORITY_SOURCE_POLICIES}

    assert "OPENDART_CORP_CODE" in namespaces
    assert "OPENDART_COMPANY_OVERVIEW" in namespaces
    assert "KR_SUPREME_COURT_IROS" in namespaces
    assert "SEC_EDGAR_ACCEPTED_FILING" in namespaces
    assert "SEC_EDGAR_LOGIN_PROVENANCE" in namespaces
    assert "US_STATE_REGISTRY_DE" in namespaces
    assert all("*" not in namespace and "?" not in namespace for namespace in namespaces)
    assert "US_STATE_REGISTRY_*" not in namespaces


def test_exact_kr_complete_path_reaches_ready_only_through_engine(database_context) -> None:
    harness = _kr_harness(database_context)
    before = _zero_snapshot(harness.sessions)

    result = harness.engine.evaluate(_kr_request(harness))

    assert result.decision.decision_state == IssuerMachineDecisionState.READY_FOR_MANUAL_REVIEW
    assert result.bridge_result.bridge_status == AuthorityBridgeStatus.ESTABLISHED
    assert result.bundle.collision_scan_result.value == "CLEAR"
    assert {
        item.authority_scope: item.scope_status for item in result.bundle.required_scope_results
    }[AuthorityScope.LEGAL_NAME].value == "SATISFIED"
    assert _zero_snapshot(harness.sessions) == before
    with pytest.raises(AuthorityReviewReadyEngineNotImplemented):
        harness.repository.insert_or_verify_decision(
            build_issuer_decision(
                bundle=result.bundle,
                decision_state=IssuerMachineDecisionState.READY_FOR_MANUAL_REVIEW,
                reason_codes=("DIRECT_CALLER_READY_ATTEMPT",),
                latest_revision_check_hash=result.decision.latest_revision_check_hash,
                freshness_policy_version=result.decision.freshness_policy_version,
                freshness_result=AuthorityFreshnessResult.CURRENT,
                collision_scan_hash=result.bundle.collision_scan_hash,
                evaluated_at=EVALUATED_AT,
                supersedes_decision_id=result.decision.issuer_decision_id,
            )
        )


def test_exact_us_complete_path_reaches_ready_and_old_filing_age_is_not_stale(
    database_context,
) -> None:
    harness = _us_harness(database_context)
    result = harness.engine.evaluate(_us_request(harness))

    assert result.decision.decision_state == IssuerMachineDecisionState.READY_FOR_MANUAL_REVIEW
    assert result.decision.freshness_result == AuthorityFreshnessResult.CURRENT
    assert result.bridge_result.bridge_status == AuthorityBridgeStatus.ESTABLISHED
    assert {
        item.authority_scope: item.scope_status for item in result.bundle.required_scope_results
    }[AuthorityScope.LEGAL_NAME].value == "SATISFIED"
    assert all(
        application.application_status
        in {
            AuthorityEvidenceApplicationStatus.APPLIED_DECISIVE,
            AuthorityEvidenceApplicationStatus.APPLIED_SUPPORTING,
        }
        for application in result.applications
    )


def test_kr_unexplained_official_legal_name_mismatch_blocks_ready(database_context) -> None:
    harness = _kr_harness(
        database_context,
        opendart_legal_name="Former Korean Corporation",
        iros_legal_name="Current Korean Corporation",
    )

    result = harness.engine.evaluate(_kr_request(harness))

    assert result.decision.decision_state == IssuerMachineDecisionState.UNRESOLVED
    assert "KR_OFFICIAL_LEGAL_NAME_CONFLICT" in result.decision.reason_codes


@pytest.mark.parametrize(
    "relation_order",
    [("subject", "name"), ("name", "subject")],
)
def test_kr_same_subject_registry_name_history_reconciles_regardless_of_relation_order(
    database_context,
    relation_order: tuple[str, ...],
) -> None:
    former_name = "Former Korean Corporation"
    harness = _kr_harness(
        database_context,
        opendart_legal_name=former_name,
        iros_legal_name="Current Korean Corporation",
    )
    _seed_decisive_legal_name_history(
        harness,
        current=harness.evidence["iros_name"],
        policy=KR_IROS_COMPLETE_POLICY,
        document_kind="VERIFIED_CORPORATE_REGISTRY_EXTRACT_V1",
        document_reference=f"iros-name-history:{KR_JURIR_NO}",
        document_group="iros-name-history-former",
        role=AuthoritySubjectRole.KOREAN_REGISTERED_LEGAL_ENTITY,
        claim_field="registry.legal_name",
        former_name=former_name,
        relation_order=relation_order,
    )

    result = harness.engine.evaluate(_kr_request(harness))

    assert result.decision.decision_state == IssuerMachineDecisionState.READY_FOR_MANUAL_REVIEW
    assert "KR_LEGAL_NAME_OFFICIAL_HISTORY_RECONCILED" in result.decision.reason_codes


def test_kr_provider_name_cannot_repair_conflicting_official_legal_names(
    database_context,
) -> None:
    harness = _kr_harness(
        database_context,
        opendart_legal_name="Korean authority subject",
        iros_legal_name="Different Court Registry Corporation",
    )

    result = harness.engine.evaluate(_kr_request(harness))

    assert result.decision.decision_state == IssuerMachineDecisionState.UNRESOLVED
    assert "KR_OFFICIAL_LEGAL_NAME_CONFLICT" in result.decision.reason_codes


def test_kr_omitted_co_current_legal_name_conflict_is_discovered(database_context) -> None:
    harness = _kr_harness(database_context)
    contradictory = _evidence(
        policy=OPENDART_COMPANY_OVERVIEW_POLICY,
        document_kind="COMPANY_OVERVIEW_JSON_V1",
        document_reference=f"company-overview:{KR_CORP_CODE}",
        document_group=f"company-overview-{KR_CORP_CODE}",
        scope=AuthorityScope.LEGAL_NAME,
        role=AuthoritySubjectRole.DART_DISCLOSURE_FILER,
        claim_field="company.corp_name",
        value="Contradictory OpenDART Corporation",
    )
    _persist_evidence(harness.repository, contradictory, fetched_at=CURRENT_FETCHED_AT)
    requested_ids = tuple(item.evidence_id for item in harness.evidence.values())
    assert contradictory.evidence_id not in requested_ids

    result = harness.engine.evaluate(_kr_request(harness, evidence_ids=requested_ids))

    assert result.decision.decision_state == IssuerMachineDecisionState.UNRESOLVED
    assert "KR_CO_CURRENT_LEGAL_NAME_CONFLICT" in result.decision.reason_codes


def test_us_unexplained_official_legal_name_mismatch_blocks_ready(database_context) -> None:
    harness = _us_harness(
        database_context,
        sec_legal_name="Former U.S. Corporation",
        state_legal_name="Current U.S. Corporation",
    )

    result = harness.engine.evaluate(_us_request(harness))

    assert result.decision.decision_state == IssuerMachineDecisionState.UNRESOLVED
    assert "US_OFFICIAL_LEGAL_NAME_CONFLICT" in result.decision.reason_codes


@pytest.mark.parametrize(
    "relation_order",
    [("subject", "name"), ("name", "subject")],
)
def test_us_same_subject_state_name_history_reconciles_regardless_of_relation_order(
    database_context,
    relation_order: tuple[str, ...],
) -> None:
    former_name = "Former U.S. Corporation"
    harness = _us_harness(
        database_context,
        sec_legal_name=former_name,
        state_legal_name="Current U.S. Corporation",
    )
    _seed_decisive_legal_name_history(
        harness,
        current=harness.evidence["state_name"],
        policy=US_STATE_REGISTRY_DE_POLICY,
        document_kind="VERIFIED_DOMESTIC_ENTITY_RECORD_V1",
        document_reference=f"de-name-history:{US_STATE_ENTITY_NUMBER}",
        document_group="de-name-history-former",
        role=AuthoritySubjectRole.US_STATE_REGISTERED_LEGAL_ENTITY,
        claim_field="registry.legal_name",
        former_name=former_name,
        relation_order=relation_order,
    )

    result = harness.engine.evaluate(_us_request(harness))

    assert result.decision.decision_state == IssuerMachineDecisionState.READY_FOR_MANUAL_REVIEW
    assert "US_LEGAL_NAME_OFFICIAL_HISTORY_RECONCILED" in result.decision.reason_codes


@pytest.mark.parametrize(
    "relation_type",
    [AuthorityEvidenceRelationType.CORRECTS, AuthorityEvidenceRelationType.SUPERSEDES],
)
def test_kr_cross_entity_name_relation_cannot_reconcile_official_names(
    database_context,
    relation_type: AuthorityEvidenceRelationType,
) -> None:
    former_name = "Former Korean Corporation"
    harness = _kr_harness(
        database_context,
        opendart_legal_name=former_name,
        iros_legal_name="Current Korean Corporation",
    )
    _seed_decisive_legal_name_history(
        harness,
        current=harness.evidence["iros_name"],
        policy=KR_IROS_COMPLETE_POLICY,
        document_kind="VERIFIED_CORPORATE_REGISTRY_EXTRACT_V1",
        document_reference="iros-name-history:1101119999999",
        document_group="iros-name-history-different-entity",
        role=AuthoritySubjectRole.KOREAN_REGISTERED_LEGAL_ENTITY,
        claim_field="registry.legal_name",
        former_name=former_name,
        kr_jurir_no="1101119999999",
        relation_type=relation_type,
    )

    result = harness.engine.evaluate(_kr_request(harness))

    assert result.decision.decision_state == IssuerMachineDecisionState.UNRESOLVED
    assert "KR_LEGAL_NAME_HISTORY_SUBJECT_BINDING_FAILED" in result.decision.reason_codes


@pytest.mark.parametrize(
    "relation_type",
    [AuthorityEvidenceRelationType.CORRECTS, AuthorityEvidenceRelationType.SUPERSEDES],
)
def test_us_other_delaware_entity_name_relation_cannot_reconcile_official_names(
    database_context,
    relation_type: AuthorityEvidenceRelationType,
) -> None:
    former_name = "Former U.S. Corporation"
    harness = _us_harness(
        database_context,
        sec_legal_name=former_name,
        state_legal_name="Current U.S. Corporation",
    )
    _seed_decisive_legal_name_history(
        harness,
        current=harness.evidence["state_name"],
        policy=US_STATE_REGISTRY_DE_POLICY,
        document_kind="VERIFIED_DOMESTIC_ENTITY_RECORD_V1",
        document_reference="de-name-history:7654321",
        document_group="de-name-history-different-entity",
        role=AuthoritySubjectRole.US_STATE_REGISTERED_LEGAL_ENTITY,
        claim_field="registry.legal_name",
        former_name=former_name,
        us_state_entity_number="7654321",
        relation_type=relation_type,
    )

    result = harness.engine.evaluate(_us_request(harness))

    assert result.decision.decision_state == IssuerMachineDecisionState.UNRESOLVED
    assert "US_LEGAL_NAME_HISTORY_SUBJECT_BINDING_FAILED" in result.decision.reason_codes


@pytest.mark.parametrize(
    ("primary_accession", "primary_name", "secondary_accession", "secondary_name", "order"),
    [
        (
            US_ACCESSION,
            "Former U.S. Corporation",
            US_SECOND_ACCESSION,
            "Current U.S. Corporation",
            ("cik", "role", "bridge", "name"),
        ),
        (
            US_SECOND_ACCESSION,
            "Current U.S. Corporation",
            US_ACCESSION,
            "Former U.S. Corporation",
            ("name", "bridge", "role", "cik"),
        ),
    ],
)
def test_every_historical_sec_name_can_be_reconciled_by_same_subject_state_history(
    database_context,
    primary_accession: str,
    primary_name: str,
    secondary_accession: str,
    secondary_name: str,
    order: tuple[str, ...],
) -> None:
    current_name = "Current U.S. Corporation"
    former_name = "Former U.S. Corporation"
    harness = _us_harness(
        database_context,
        label=f"us_multi_name_{primary_accession[-6:]}",
        accession=primary_accession,
        sec_legal_name=primary_name,
        state_legal_name=current_name,
    )
    _append_us_accepted_filing(
        harness,
        accession=secondary_accession,
        legal_name=secondary_name,
        insertion_order=order,
    )
    _seed_decisive_legal_name_history(
        harness,
        current=harness.evidence["state_name"],
        policy=US_STATE_REGISTRY_DE_POLICY,
        document_kind="VERIFIED_DOMESTIC_ENTITY_RECORD_V1",
        document_reference=f"de-name-history:{US_STATE_ENTITY_NUMBER}",
        document_group="de-name-history-multiple-sec-filings",
        role=AuthoritySubjectRole.US_STATE_REGISTERED_LEGAL_ENTITY,
        claim_field="registry.legal_name",
        former_name=former_name,
        relation_order=("name", "subject"),
    )

    result = harness.engine.evaluate(_us_request(harness))

    assert result.decision.decision_state == IssuerMachineDecisionState.READY_FOR_MANUAL_REVIEW
    assert "US_LEGAL_NAME_OFFICIAL_HISTORY_RECONCILED" in result.decision.reason_codes
    assert result.decision.freshness_result == AuthorityFreshnessResult.CURRENT


def test_one_unexplained_name_among_multiple_sec_filings_blocks_ready(database_context) -> None:
    current_name = "Current U.S. Corporation"
    former_name = "Former U.S. Corporation"
    harness = _us_harness(
        database_context,
        sec_legal_name=current_name,
        state_legal_name=current_name,
    )
    _append_us_accepted_filing(
        harness,
        accession=US_SECOND_ACCESSION,
        legal_name=former_name,
    )
    _append_us_accepted_filing(
        harness,
        accession=US_THIRD_ACCESSION,
        legal_name="Unknown U.S. Corporation",
    )
    _seed_decisive_legal_name_history(
        harness,
        current=harness.evidence["state_name"],
        policy=US_STATE_REGISTRY_DE_POLICY,
        document_kind="VERIFIED_DOMESTIC_ENTITY_RECORD_V1",
        document_reference=f"de-name-history:{US_STATE_ENTITY_NUMBER}",
        document_group="de-name-history-does-not-explain-unknown",
        role=AuthoritySubjectRole.US_STATE_REGISTERED_LEGAL_ENTITY,
        claim_field="registry.legal_name",
        former_name=former_name,
    )

    result = harness.engine.evaluate(_us_request(harness))

    assert result.decision.decision_state == IssuerMachineDecisionState.UNRESOLVED
    assert "US_OFFICIAL_LEGAL_NAME_CONFLICT" in result.decision.reason_codes


def test_multiple_sec_legal_names_without_official_state_history_conflict(
    database_context,
) -> None:
    harness = _us_harness(
        database_context,
        sec_legal_name="Current U.S. Corporation",
        state_legal_name="Current U.S. Corporation",
    )
    _append_us_accepted_filing(
        harness,
        accession=US_SECOND_ACCESSION,
        legal_name="Former U.S. Corporation",
    )

    result = harness.engine.evaluate(_us_request(harness))

    assert result.decision.decision_state == IssuerMachineDecisionState.UNRESOLVED
    assert "US_OFFICIAL_LEGAL_NAME_CONFLICT" in result.decision.reason_codes


def test_multiple_opendart_names_all_require_same_iros_subject_history(
    database_context,
) -> None:
    current_name = "Current Korean Corporation"
    former_name = "Former Korean Corporation"
    harness = _kr_harness(
        database_context,
        opendart_legal_name=current_name,
        iros_legal_name=current_name,
    )
    historical_overview_name = _evidence(
        policy=OPENDART_COMPANY_OVERVIEW_POLICY,
        document_kind="COMPANY_OVERVIEW_JSON_V1",
        document_reference=f"company-overview:{KR_CORP_CODE}",
        document_group=f"company-overview-{KR_CORP_CODE}",
        scope=AuthorityScope.LEGAL_NAME,
        role=AuthoritySubjectRole.DART_DISCLOSURE_FILER,
        claim_field="company.corp_name",
        value=former_name,
    )
    _persist_evidence(
        harness.repository,
        historical_overview_name,
        fetched_at=CURRENT_FETCHED_AT,
    )
    _seed_decisive_legal_name_history(
        harness,
        current=harness.evidence["iros_name"],
        policy=KR_IROS_COMPLETE_POLICY,
        document_kind="VERIFIED_CORPORATE_REGISTRY_EXTRACT_V1",
        document_reference=f"iros-name-history:{KR_JURIR_NO}",
        document_group="iros-name-history-multiple-opendart-names",
        role=AuthoritySubjectRole.KOREAN_REGISTERED_LEGAL_ENTITY,
        claim_field="registry.legal_name",
        former_name=former_name,
    )
    reversed_seed_ids = tuple(
        reversed(tuple(item.evidence_id for item in harness.evidence.values()))
    )

    result = harness.engine.evaluate(_kr_request(harness, evidence_ids=reversed_seed_ids))

    assert result.decision.decision_state == IssuerMachineDecisionState.READY_FOR_MANUAL_REVIEW
    assert "KR_LEGAL_NAME_OFFICIAL_HISTORY_RECONCILED" in result.decision.reason_codes


def test_us_provider_name_and_ticker_cannot_repair_official_name_conflict(
    database_context,
) -> None:
    harness = _us_harness(
        database_context,
        sec_legal_name="U.S. authority subject",
        state_legal_name="Different State Registry Corporation",
        provider_symbol=US_SYMBOL,
    )

    result = harness.engine.evaluate(_us_request(harness))

    assert result.decision.decision_state == IssuerMachineDecisionState.UNRESOLVED
    assert "US_OFFICIAL_LEGAL_NAME_CONFLICT" in result.decision.reason_codes


def test_us_omitted_co_current_state_legal_name_conflict_is_discovered(
    database_context,
) -> None:
    harness = _us_harness(database_context)
    reference = f"de-verified-entity:{US_STATE_ENTITY_NUMBER}"
    contradictory = _evidence(
        policy=US_STATE_REGISTRY_DE_POLICY,
        document_kind="VERIFIED_DOMESTIC_ENTITY_RECORD_V1",
        document_reference=reference,
        document_group=f"de-entity-{US_STATE_ENTITY_NUMBER}",
        scope=AuthorityScope.LEGAL_NAME,
        role=AuthoritySubjectRole.US_STATE_REGISTERED_LEGAL_ENTITY,
        claim_field="registry.legal_name",
        value="Contradictory Delaware Corporation",
    )
    _persist_evidence(harness.repository, contradictory, fetched_at=CURRENT_FETCHED_AT)
    requested_ids = tuple(item.evidence_id for item in harness.evidence.values())
    assert contradictory.evidence_id not in requested_ids

    result = harness.engine.evaluate(_us_request(harness, evidence_ids=requested_ids))

    assert result.decision.decision_state == IssuerMachineDecisionState.UNRESOLVED
    assert "US_CO_CURRENT_LEGAL_NAME_CONFLICT" in result.decision.reason_codes


@pytest.mark.parametrize(
    ("primary_accession", "secondary_accession", "secondary_fact_order"),
    [
        (US_ACCESSION, US_SECOND_ACCESSION, ("cik", "role", "bridge", "name")),
        (US_SECOND_ACCESSION, US_ACCESSION, ("name", "bridge", "role", "cik")),
    ],
)
def test_compatible_historical_sec_filings_do_not_conflict_by_accession_or_order(
    database_context,
    primary_accession: str,
    secondary_accession: str,
    secondary_fact_order: tuple[str, ...],
) -> None:
    harness = _us_harness(
        database_context,
        label="us_compatible_multiple_filings",
        accession=primary_accession,
    )
    second = _append_us_accepted_filing(
        harness,
        accession=secondary_accession,
        insertion_order=secondary_fact_order,
    )
    requested_ids = tuple(item.evidence_id for item in harness.evidence.values())
    assert not {item.evidence_id for item in second.values()}.intersection(requested_ids)

    result = harness.engine.evaluate(_us_request(harness, evidence_ids=requested_ids))

    assert result.decision.decision_state == IssuerMachineDecisionState.READY_FOR_MANUAL_REVIEW
    assert "US_CO_CURRENT_AUTHORITY_CONFLICT" not in result.decision.reason_codes
    assert result.bridge_result.bridge_status == AuthorityBridgeStatus.ESTABLISHED


def test_historical_sec_filings_with_different_state_entity_numbers_conflict(
    database_context,
) -> None:
    harness = _us_harness(database_context)
    _append_us_accepted_filing(
        harness,
        accession=US_SECOND_ACCESSION,
        state_entity_number="7654321",
    )

    result = harness.engine.evaluate(_us_request(harness))

    assert result.decision.decision_state == IssuerMachineDecisionState.UNRESOLVED
    assert "US_SEC_BRIDGE_IDENTITY_CONFLICT" in result.decision.reason_codes


def test_historical_sec_filings_with_incompatible_formation_states_conflict(
    database_context,
) -> None:
    harness = _us_harness(database_context)
    _append_us_accepted_filing(
        harness,
        accession=US_SECOND_ACCESSION,
        formation_state="CA",
    )

    result = harness.engine.evaluate(_us_request(harness))

    assert result.decision.decision_state == IssuerMachineDecisionState.UNRESOLVED
    assert "US_SEC_BRIDGE_IDENTITY_CONFLICT" in result.decision.reason_codes


def test_historical_former_symbol_is_reconciled_by_authority_acceptance_history(
    database_context,
) -> None:
    current_accepted_at = datetime(2026, 8, 1, tzinfo=UTC)
    harness = _us_harness(
        database_context,
        accession=US_SECOND_ACCESSION,
        filing_accepted_at=current_accepted_at,
    )
    _append_us_accepted_filing(
        harness,
        accession=US_ACCESSION,
        provider_symbol="FORMER",
        accepted_at=datetime(2024, 8, 1, tzinfo=UTC),
    )

    result = harness.engine.evaluate(_us_request(harness))

    assert result.decision.decision_state == IssuerMachineDecisionState.READY_FOR_MANUAL_REVIEW
    assert "US_PROVIDER_SYMBOL_HISTORY_UNRECONCILED" not in result.decision.reason_codes


def test_unreconciled_multiple_sec_provider_symbols_fail_closed(database_context) -> None:
    harness = _us_harness(database_context)
    _append_us_accepted_filing(
        harness,
        accession=US_SECOND_ACCESSION,
        provider_symbol="FORMER",
    )

    result = harness.engine.evaluate(_us_request(harness))

    assert result.decision.decision_state == IssuerMachineDecisionState.UNRESOLVED
    assert "US_PROVIDER_SYMBOL_HISTORY_UNRECONCILED" in result.decision.reason_codes


def test_historical_filing_age_and_accession_are_separate_from_latest_status_freshness(
    database_context,
) -> None:
    harness = _us_harness(
        database_context,
        filing_accepted_at=datetime(2010, 1, 1, tzinfo=UTC),
        current_fetched_at=CURRENT_FETCHED_AT,
    )

    result = harness.engine.evaluate(_us_request(harness))

    assert result.decision.decision_state == IssuerMachineDecisionState.READY_FOR_MANUAL_REVIEW
    assert result.decision.freshness_result == AuthorityFreshnessResult.CURRENT
    assert harness.evidence["bridge"].authority_accepted_at == datetime(2010, 1, 1, tzinfo=UTC)


@pytest.mark.parametrize(
    ("options", "expected_reason"),
    [
        ({"include_iros": False}, "MISSING_KR_IROS_JURISDICTION"),
        ({"iros_verified": False}, "LEGAL_JURISDICTION_UNUSABLE"),
        ({"overview_jurir": "1101119999999"}, "KR_EXACT_REGISTRY_PROVIDER_BRIDGE_MISMATCH"),
        ({"iros_entity_kind": "FOREIGN_COMPANY_BRANCH"}, "LEGAL_JURISDICTION_UNUSABLE"),
        ({"overview_mode": "NAME_ONLY"}, "MISSING_KR_OVERVIEW_BRIDGE"),
        ({"overview_mode": "SYMBOL_ONLY"}, "MISSING_KR_OVERVIEW_BRIDGE"),
        ({"overview_symbol": "000660"}, "KR_EXACT_REGISTRY_PROVIDER_BRIDGE_MISMATCH"),
    ],
)
def test_kr_incomplete_or_non_authoritative_paths_fail_closed(
    database_context,
    options: dict[str, Any],
    expected_reason: str,
) -> None:
    harness = _kr_harness(database_context, **options)
    result = harness.engine.evaluate(_kr_request(harness))

    assert result.decision.decision_state == IssuerMachineDecisionState.UNRESOLVED
    assert expected_reason in result.decision.reason_codes


@pytest.mark.parametrize(
    ("options", "expected_state", "expected_reason"),
    [
        (
            {"include_state": False},
            IssuerMachineDecisionState.UNRESOLVED,
            "MISSING_US_STATE_JURISDICTION",
        ),
        (
            {"state_record_kind": "FOREIGN_QUALIFICATION"},
            IssuerMachineDecisionState.UNRESOLVED,
            "LEGAL_JURISDICTION_UNUSABLE",
        ),
        (
            {"state_value": "CA"},
            IssuerMachineDecisionState.UNRESOLVED,
            "LEGAL_JURISDICTION_UNUSABLE",
        ),
        (
            {"sec_bridge_mode": "NAME_ONLY"},
            IssuerMachineDecisionState.UNRESOLVED,
            "MISSING_US_SEC_BRIDGE",
        ),
        (
            {"sec_bridge_mode": "TICKER_ONLY"},
            IssuerMachineDecisionState.UNRESOLVED,
            "MISSING_US_SEC_BRIDGE",
        ),
        (
            {"provider_symbol": "NVDA"},
            IssuerMachineDecisionState.UNRESOLVED,
            "US_EXACT_STATE_SEC_PROVIDER_BRIDGE_MISMATCH",
        ),
        (
            {"include_latest_status": False},
            IssuerMachineDecisionState.STALE,
            "US_CURRENT_STATUS_CHECK_MISSING",
        ),
    ],
)
def test_us_incomplete_or_non_authoritative_paths_fail_closed(
    database_context,
    options: dict[str, Any],
    expected_state: IssuerMachineDecisionState,
    expected_reason: str,
) -> None:
    harness = _us_harness(database_context, **options)
    result = harness.engine.evaluate(_us_request(harness))

    assert result.decision.decision_state == expected_state
    assert expected_reason in result.decision.reason_codes


@pytest.mark.parametrize(
    ("factory", "request_factory"),
    [
        (
            lambda database_context: _kr_harness(
                database_context, current_fetched_at=STALE_FETCHED_AT
            ),
            _kr_request,
        ),
        (
            lambda database_context: _us_harness(
                database_context, current_fetched_at=STALE_FETCHED_AT
            ),
            _us_request,
        ),
    ],
)
def test_stale_current_status_blocks_ready_but_historical_fact_age_does_not(
    database_context,
    factory,
    request_factory,
) -> None:
    harness = factory(database_context)
    result = harness.engine.evaluate(request_factory(harness))

    assert result.decision.decision_state == IssuerMachineDecisionState.STALE
    assert result.decision.freshness_result == AuthorityFreshnessResult.STALE


def test_unavailable_required_current_check_is_stale(database_context) -> None:
    harness = _kr_harness(
        database_context,
        current_status=AuthorityRetrievalStatus.UNAVAILABLE,
    )
    result = harness.engine.evaluate(_kr_request(harness))

    assert result.decision.decision_state == IssuerMachineDecisionState.STALE
    assert result.decision.freshness_result == AuthorityFreshnessResult.UNAVAILABLE


@pytest.mark.parametrize(
    "caller_time",
    [EVALUATED_AT - timedelta(days=30), EVALUATED_AT + timedelta(days=30)],
)
def test_caller_time_cannot_backdate_or_force_freshness(
    database_context,
    caller_time: datetime,
) -> None:
    harness = _kr_harness(database_context, current_fetched_at=STALE_FETCHED_AT)
    request_values = _kr_request(harness).model_dump(mode="python")

    with pytest.raises(ValidationError):
        IssuerAuthorityEvaluationRequest.model_validate(
            {**request_values, "evaluated_at": caller_time}
        )

    result = harness.engine.evaluate(_kr_request(harness))

    assert result.decision.decision_state == IssuerMachineDecisionState.STALE
    assert result.decision.freshness_result == AuthorityFreshnessResult.STALE
    assert result.decision.evaluated_at == EVALUATED_AT


def test_server_clock_is_injected_once_and_never_becomes_authority_effective_time(
    database_context,
) -> None:
    harness = _kr_harness(database_context)
    evidence_before = harness.repository.evidence(harness.evidence["overview"].evidence_id)
    harness.clock.value = EVALUATED_AT + timedelta(minutes=7)

    result = harness.engine.evaluate(_kr_request(harness))
    evidence_after = harness.repository.evidence(harness.evidence["overview"].evidence_id)

    assert result.decision.evaluated_at == EVALUATED_AT + timedelta(minutes=7)
    assert evidence_after == evidence_before
    assert evidence_after.authority_effective_at is None
    assert evidence_after.authority_effective_date is None


def test_format_valid_unproven_identifiers_and_known_synthetic_values_fail_closed(
    database_context,
) -> None:
    harness = _kr_harness(database_context)
    unproven = harness.engine.evaluate(
        _kr_request(harness, identifier_value="12345678", evidence_ids=())
    )

    assert unproven.decision.decision_state == IssuerMachineDecisionState.UNRESOLVED
    with pytest.raises(IssuerAuthorityDecisionEngineError, match="SYNTHETIC_IDENTIFIER_PROHIBITED"):
        harness.engine.evaluate(_kr_request(harness, identifier_value="90000001", evidence_ids=()))


def test_normal_repository_cannot_select_or_create_production_admission(
    database_context,
) -> None:
    sessions = session_factory(database_context.engine)
    repository = SQLiteAuthorityLedgerRepository(sessions)

    with pytest.raises(TypeError):
        SQLiteAuthorityLedgerRepository(sessions, mode="PRODUCTION_AUTHORITY")  # type: ignore[call-arg]
    with pytest.raises(
        AuthorityProductionAdmissionUnavailable,
        match="PRODUCTION_AUTHORITY_ADMISSION_UNAVAILABLE",
    ):
        repository.insert_or_verify_source_policy(OPENDART_CORP_CODE_POLICY)

    seed_preadmitted_authority_snapshot(
        sessions,
        policies=(OPENDART_CORP_CODE_POLICY,),
    )
    locally_constructed = _evidence(
        policy=OPENDART_CORP_CODE_POLICY,
        document_kind="CORP_CODE_XML_V1",
        document_reference=f"corp-code:{KR_CORP_CODE}",
        document_group="caller-constructed-production-fact",
        scope=AuthorityScope.ISSUER_REGULATORY_ID,
        role=AuthoritySubjectRole.DART_DISCLOSURE_FILER,
        claim_field="corp_list.corp.corp_code",
        value=KR_CORP_CODE,
    )
    with pytest.raises(
        AuthorityProductionAdmissionUnavailable,
        match="PRODUCTION_AUTHORITY_ADMISSION_UNAVAILABLE",
    ):
        repository.insert_or_verify_evidence(locally_constructed)
    seed_preadmitted_authority_snapshot(sessions, evidence=(locally_constructed,))
    observation = build_authority_evidence_observation(
        evidence_id=locally_constructed.evidence_id,
        fetched_at=CURRENT_FETCHED_AT,
        raw_content_hash=locally_constructed.raw_content_hash,
        authority_source_locator=locally_constructed.authority_source_locator,
        authority_document_reference=locally_constructed.authority_document_reference,
        retrieval_status=AuthorityRetrievalStatus.SUCCEEDED,
        secret_free_retrieval_fingerprint=authority_sha256({"caller_observation": True}),
        safe_status_code="OK",
    )
    with pytest.raises(AuthorityProductionAdmissionUnavailable):
        repository.insert_or_verify_evidence_observation(observation)

    corrected = _evidence(
        policy=OPENDART_CORP_CODE_POLICY,
        document_kind="CORP_CODE_XML_V1",
        document_reference=f"corp-code:{KR_CORP_CODE}:corrected",
        document_group="caller-constructed-correction",
        scope=AuthorityScope.ISSUER_REGULATORY_ID,
        role=AuthoritySubjectRole.DART_DISCLOSURE_FILER,
        claim_field="corp_list.corp.corp_code",
        value=KR_CORP_CODE,
        evidence_kind=AuthorityEvidenceKind.CORRECTION,
    )
    seed_preadmitted_authority_snapshot(sessions, evidence=(corrected,))
    relation = build_authority_evidence_relation(
        predecessor_evidence_id=locally_constructed.evidence_id,
        successor_evidence_id=corrected.evidence_id,
        relation_type=AuthorityEvidenceRelationType.CORRECTS,
        recorded_at=EVALUATED_AT,
        authority_effective_missing_reason=(AuthorityTimeMissingReason.NOT_SUPPLIED_BY_AUTHORITY),
    )
    with pytest.raises(AuthorityProductionAdmissionUnavailable):
        repository.insert_or_verify_evidence_relation(relation)

    production_root = Path("services/api/src")
    assert all(
        "authority_preadmitted_ledger" not in path.read_text(encoding="utf-8")
        for path in production_root.rglob("*.py")
    )


def test_fixture_and_relabelled_fixture_lineage_cannot_enter_ready(database_context) -> None:
    harness = _kr_harness(database_context)
    policy = fixture_source_policy()
    harness.repository.insert_or_verify_source_policy(policy)
    fixture_only_code = "00126381"
    tainted = build_authority_evidence(
        authority_source_policy_id=policy.authority_source_policy_id,
        authority_source_identifier=policy.source_namespace,
        authority_classification=policy.authority_classification,
        authority_source_locator="fixture://authority/relabelled-opendart.json",
        authority_document_reference="copied-fixture",
        source_document_kind=policy.allowed_document_kinds[0],
        authority_external_key="copied-fixture",
        raw_content_hash=authority_sha256({"copied_fixture": True}),
        parser_contract_version=policy.admitted_parser_contract_versions[0],
        evidence_kind=AuthorityEvidenceKind.PROVENANCE_ONLY,
        authority_scope=AuthorityScope.ISSUER_REGULATORY_ID,
        subject_role=AuthoritySubjectRole.DART_DISCLOSURE_FILER,
        policy_maximum_issuer_authority_weight=AuthorityWeight.ZERO,
        claim_field="corp_list.corp.corp_code",
        raw_claim_value=fixture_only_code,
        normalized_claim_value=fixture_only_code,
        authority_published_at=None,
        authority_accepted_at=None,
        authority_as_of_date=None,
        authority_effective_at=None,
        authority_effective_date=None,
        authority_time_missing_reasons=_missing_times(),
        access_disposition=policy.required_access_disposition,
        license_disposition=policy.required_license_disposition,
        origin_data_mode=AuthorityOriginDataMode.TEST_ONLY,
        origin_adapter_class=policy.admitted_adapter_contract_versions[0],
        origin_source_system="FIXTURE_KR_REGULATOR",
        lineage_tainted=True,
        lineage_ancestor_tainted=True,
        lineage_ancestor_hashes=(authority_sha256({"fixture_ancestor": 1}),),
    )
    _persist_evidence(harness.repository, tainted, fetched_at=CURRENT_FETCHED_AT)
    result = harness.engine.evaluate(
        _kr_request(
            harness,
            identifier_value=fixture_only_code,
            evidence_ids=(tainted.evidence_id,),
        )
    )

    assert result.decision.decision_state == IssuerMachineDecisionState.UNRESOLVED
    assert not result.bundle.evidence_application_members


def test_login_and_filing_agent_cik_remain_zero_weight_provenance(database_context) -> None:
    harness = _us_harness(database_context)
    seed_preadmitted_authority_snapshot(
        harness.sessions,
        policies=(SEC_LOGIN_PROVENANCE_POLICY,),
    )
    provenance = _evidence(
        policy=SEC_LOGIN_PROVENANCE_POLICY,
        document_kind="SEC_SUBMISSION_PROVENANCE_JSON_V1",
        document_reference=US_ACCESSION,
        document_group="sec-login-provenance",
        scope=AuthorityScope.SUBMISSION_PROVENANCE,
        role=AuthoritySubjectRole.SEC_LOGIN_CIK,
        claim_field="submission.login_cik",
        value="0000123456",
        evidence_kind=AuthorityEvidenceKind.PROVENANCE_ONLY,
    )
    _persist_evidence(harness.repository, provenance, fetched_at=CURRENT_FETCHED_AT)
    result = harness.engine.evaluate(
        _us_request(
            harness,
            evidence_ids=tuple(
                [item.evidence_id for item in harness.evidence.values()] + [provenance.evidence_id]
            ),
        )
    )

    provenance_applications = [
        application
        for application in result.applications
        if application.evidence_id == provenance.evidence_id
    ]
    assert (
        provenance_applications[0].application_status
        == AuthorityEvidenceApplicationStatus.PROVENANCE_ONLY
    )
    assert provenance_applications[0].effective_issuer_authority_weight == AuthorityWeight.ZERO
    assert result.decision.decision_state == IssuerMachineDecisionState.READY_FOR_MANUAL_REVIEW


def test_request_rejects_force_override_and_caller_authority_fields(database_context) -> None:
    harness = _kr_harness(database_context)
    values = _kr_request(harness).model_dump(mode="python")

    for field, value in (
        ("force", True),
        ("override", True),
        ("authority_weight", "DECISIVE"),
        ("bridge_ok", True),
        ("is_ready", True),
        ("evaluated_at", EVALUATED_AT - timedelta(days=30)),
    ):
        with pytest.raises(ValidationError):
            IssuerAuthorityEvaluationRequest.model_validate({**values, field: value})


def test_input_order_and_evaluation_clock_do_not_change_semantic_identity(
    database_context,
) -> None:
    harness = _kr_harness(database_context)
    evidence_ids = tuple(item.evidence_id for item in harness.evidence.values())
    first = harness.engine.evaluate(
        _kr_request(harness, evidence_ids=tuple(reversed(evidence_ids)))
    )
    harness.clock.value = EVALUATED_AT + timedelta(minutes=1)
    replay = harness.engine.evaluate(_kr_request(harness, evidence_ids=evidence_ids))

    assert first.bundle.authority_bundle_id == replay.bundle.authority_bundle_id
    assert first.decision.issuer_decision_id == replay.decision.issuer_decision_id
    assert replay.decision_inserted is False


def test_authority_supplied_semantic_time_changes_evidence_identity() -> None:
    base = _evidence(
        policy=OPENDART_CORP_CODE_POLICY,
        document_kind="CORP_CODE_XML_V1",
        document_reference=f"corp-code:{KR_CORP_CODE}",
        document_group="semantic-authority-time",
        scope=AuthorityScope.ISSUER_REGULATORY_ID,
        role=AuthoritySubjectRole.DART_DISCLOSURE_FILER,
        claim_field="corp_list.corp.corp_code",
        value=KR_CORP_CODE,
    )
    values = base.model_dump(mode="python")
    for computed in ("evidence_id", "evidence_content_hash", "evidence_provenance_hash"):
        values.pop(computed)
    values["authority_accepted_at"] = EVALUATED_AT
    values["authority_time_missing_reasons"].pop("authority_accepted_at")
    changed = build_authority_evidence(**values)

    assert changed.evidence_id != base.evidence_id


def test_all_global_write_counters_remain_zero(database_context) -> None:
    harness = _kr_harness(database_context)
    before = _zero_snapshot(harness.sessions)
    harness.engine.evaluate(_kr_request(harness))

    assert _zero_snapshot(harness.sessions) == before


@pytest.mark.parametrize("reverse_seed_order", [False, True])
def test_kr_co_current_overview_conflict_is_discovered_when_omitted_from_request(
    database_context,
    reverse_seed_order: bool,
) -> None:
    harness = _kr_harness(database_context)
    contradictory = _evidence(
        policy=OPENDART_COMPANY_OVERVIEW_POLICY,
        document_kind="COMPANY_OVERVIEW_JSON_V1",
        document_reference=f"company-overview:{KR_CORP_CODE}",
        document_group="company-overview-conflicting-jurir",
        scope=AuthorityScope.LEGAL_ENTITY_BRIDGE,
        role=AuthoritySubjectRole.DART_DISCLOSURE_FILER,
        claim_field="company.identity_bridge",
        value={
            "corp_code": KR_CORP_CODE,
            "jurir_no": "1101119999999",
            "stock_code": KR_SYMBOL,
        },
    )
    _persist_evidence(harness.repository, contradictory, fetched_at=CURRENT_FETCHED_AT)
    seed_ids = tuple(item.evidence_id for item in harness.evidence.values())
    if reverse_seed_order:
        seed_ids = tuple(reversed(seed_ids))

    result = harness.engine.evaluate(_kr_request(harness, evidence_ids=seed_ids))

    assert contradictory.evidence_id not in seed_ids
    assert result.decision.decision_state == IssuerMachineDecisionState.UNRESOLVED
    assert "KR_CO_CURRENT_AUTHORITY_CONFLICT" in result.decision.reason_codes


def test_kr_co_current_iros_disagreement_blocks_matching_path(database_context) -> None:
    harness = _kr_harness(database_context)
    reference = f"iros-verified-original:{KR_JURIR_NO}:conflicting-status"
    contradictory = _evidence(
        policy=KR_IROS_COMPLETE_POLICY,
        document_kind="VERIFIED_CORPORATE_REGISTRY_EXTRACT_V1",
        document_reference=reference,
        document_group="iros-conflicting-current-status",
        scope=AuthorityScope.LEGAL_JURISDICTION,
        role=AuthoritySubjectRole.KOREAN_REGISTERED_LEGAL_ENTITY,
        claim_field="registry.legal_entity_status",
        value={
            "corporate_registration_reference": KR_JURIR_NO,
            "entity_kind": "FOREIGN_COMPANY_BRANCH",
            "jurisdiction": "KR",
            "verification_reference": reference,
        },
    )
    _persist_evidence(harness.repository, contradictory, fetched_at=CURRENT_FETCHED_AT)

    result = harness.engine.evaluate(_kr_request(harness))

    assert contradictory.evidence_id not in _kr_request(harness).evidence_ids
    assert result.decision.decision_state == IssuerMachineDecisionState.UNRESOLVED
    assert "KR_CO_CURRENT_AUTHORITY_CONFLICT" in result.decision.reason_codes


def test_us_co_current_sec_bridge_conflict_blocks_one_matching_state_record(
    database_context,
) -> None:
    harness = _us_harness(database_context)
    contradictory = _evidence(
        policy=SEC_ACCEPTED_FILING_POLICY,
        document_kind="SEC_ACCEPTED_ISSUER_FILING_JSON_V1",
        document_reference=US_ACCESSION,
        document_group="sec-conflicting-current-bridge",
        scope=AuthorityScope.LEGAL_ENTITY_BRIDGE,
        role=AuthoritySubjectRole.SEC_REGISTRANT,
        claim_field="filing.legal_entity_bridge",
        value={
            "accepted_accession": US_ACCESSION,
            "formation_state": "CA",
            "provider_symbol": US_SYMBOL,
            "registrant_cik": US_CIK,
            "state_entity_number": "7654321",
        },
    )
    _persist_evidence(harness.repository, contradictory, fetched_at=HISTORICAL_FETCHED_AT)

    result = harness.engine.evaluate(_us_request(harness))

    assert result.decision.decision_state == IssuerMachineDecisionState.UNRESOLVED
    assert "US_CO_CURRENT_AUTHORITY_CONFLICT" in result.decision.reason_codes


def test_us_conflicting_latest_status_facts_block_ready(database_context) -> None:
    harness = _us_harness(database_context)
    accession = "0000789019-26-000003"
    contradictory = _evidence(
        policy=SEC_ACCEPTED_FILING_POLICY,
        document_kind="SEC_REGISTRANT_LATEST_STATUS_JSON_V1",
        document_reference=accession,
        document_group="sec-conflicting-latest-status",
        scope=AuthorityScope.REGISTRANT_ROLE,
        role=AuthoritySubjectRole.SEC_REGISTRANT,
        claim_field="registrant.latest_filing_status",
        value={
            "latest_accession": accession,
            "registrant_cik": US_CIK,
            "status": "CURRENT",
        },
    )
    _persist_evidence(harness.repository, contradictory, fetched_at=CURRENT_FETCHED_AT)

    result = harness.engine.evaluate(_us_request(harness))

    assert result.decision.decision_state == IssuerMachineDecisionState.UNRESOLVED
    assert "US_CO_CURRENT_AUTHORITY_CONFLICT" in result.decision.reason_codes


def test_us_conflicting_current_state_registry_fact_blocks_ready(database_context) -> None:
    harness = _us_harness(database_context)
    reference = f"de-verified-entity:{US_STATE_ENTITY_NUMBER}:foreign-qualification"
    contradictory = _evidence(
        policy=US_STATE_REGISTRY_DE_POLICY,
        document_kind="VERIFIED_DOMESTIC_ENTITY_RECORD_V1",
        document_reference=reference,
        document_group="de-conflicting-current-record",
        scope=AuthorityScope.LEGAL_JURISDICTION,
        role=AuthoritySubjectRole.US_STATE_REGISTERED_LEGAL_ENTITY,
        claim_field="registry.legal_entity_status",
        value={
            "formation_state": "DE",
            "jurisdiction": "US",
            "record_kind": "FOREIGN_QUALIFICATION",
            "state_entity_number": US_STATE_ENTITY_NUMBER,
            "status": "ACTIVE",
            "verification_reference": reference,
        },
    )
    _persist_evidence(harness.repository, contradictory, fetched_at=CURRENT_FETCHED_AT)

    result = harness.engine.evaluate(_us_request(harness))

    assert result.decision.decision_state == IssuerMachineDecisionState.UNRESOLVED
    assert "US_CO_CURRENT_AUTHORITY_CONFLICT" in result.decision.reason_codes


def _append_corrected_iros(
    harness: _Harness,
    *,
    suffix: str,
) -> tuple[AuthorityEvidence, AuthorityEvidence, AuthorityEvidence]:
    reference = f"iros-verified-original:{KR_JURIR_NO}:{suffix}"
    jurisdiction = _evidence(
        policy=KR_IROS_COMPLETE_POLICY,
        document_kind="VERIFIED_CORPORATE_REGISTRY_EXTRACT_V1",
        document_reference=reference,
        document_group=f"iros-corrected-{suffix}",
        scope=AuthorityScope.LEGAL_JURISDICTION,
        role=AuthoritySubjectRole.KOREAN_REGISTERED_LEGAL_ENTITY,
        claim_field="registry.legal_entity_status",
        value={
            "corporate_registration_reference": KR_JURIR_NO,
            "entity_kind": "DOMESTIC_CORPORATION",
            "jurisdiction": "KR",
            "verification_reference": reference,
        },
        evidence_kind=AuthorityEvidenceKind.CORRECTION,
    )
    bridge = _evidence(
        policy=KR_IROS_COMPLETE_POLICY,
        document_kind="VERIFIED_CORPORATE_REGISTRY_EXTRACT_V1",
        document_reference=reference,
        document_group=f"iros-corrected-{suffix}",
        scope=AuthorityScope.LEGAL_ENTITY_BRIDGE,
        role=AuthoritySubjectRole.KOREAN_REGISTERED_LEGAL_ENTITY,
        claim_field="registry.corporate_registration_reference",
        value=KR_JURIR_NO,
        evidence_kind=AuthorityEvidenceKind.CORRECTION,
    )
    legal_name = _evidence(
        policy=KR_IROS_COMPLETE_POLICY,
        document_kind="VERIFIED_CORPORATE_REGISTRY_EXTRACT_V1",
        document_reference=reference,
        document_group=f"iros-corrected-{suffix}",
        scope=AuthorityScope.LEGAL_NAME,
        role=AuthoritySubjectRole.KOREAN_REGISTERED_LEGAL_ENTITY,
        claim_field="registry.legal_name",
        value=KR_LEGAL_NAME,
        evidence_kind=AuthorityEvidenceKind.CORRECTION,
    )
    for item in (jurisdiction, bridge, legal_name):
        _persist_evidence(harness.repository, item, fetched_at=CURRENT_FETCHED_AT)
    relations = tuple(
        build_authority_evidence_relation(
            predecessor_evidence_id=predecessor.evidence_id,
            successor_evidence_id=successor.evidence_id,
            relation_type=AuthorityEvidenceRelationType.CORRECTS,
            recorded_at=EVALUATED_AT,
            authority_effective_missing_reason=(
                AuthorityTimeMissingReason.NOT_SUPPLIED_BY_AUTHORITY
            ),
        )
        for predecessor, successor in (
            (harness.evidence["iros_jurisdiction"], jurisdiction),
            (harness.evidence["iros_bridge"], bridge),
            (harness.evidence["iros_name"], legal_name),
        )
    )
    seed_preadmitted_authority_snapshot(
        harness.sessions,
        relations=relations,
    )
    return jurisdiction, bridge, legal_name


def test_correction_recomputes_relation_head_and_appends_new_bundle_decision_chain(
    database_context,
) -> None:
    harness = _kr_harness(database_context)
    initial = harness.engine.evaluate(_kr_request(harness))
    corrected_jurisdiction, corrected_bridge, corrected_name = _append_corrected_iros(
        harness, suffix="v2"
    )

    harness.clock.value = EVALUATED_AT + timedelta(minutes=1)
    invalidated = harness.engine.evaluate(_kr_request(harness))
    corrected_ids = (
        *(
            item.evidence_id
            for key, item in harness.evidence.items()
            if key not in {"iros_jurisdiction", "iros_bridge", "iros_name"}
        ),
        corrected_jurisdiction.evidence_id,
        corrected_bridge.evidence_id,
        corrected_name.evidence_id,
    )
    harness.clock.value = EVALUATED_AT + timedelta(minutes=2)
    corrected = harness.engine.evaluate(_kr_request(harness, evidence_ids=corrected_ids))

    assert initial.decision.decision_state == IssuerMachineDecisionState.READY_FOR_MANUAL_REVIEW
    assert invalidated.decision.decision_state == IssuerMachineDecisionState.REVIEW_REQUIRED
    assert corrected.decision.decision_state == IssuerMachineDecisionState.READY_FOR_MANUAL_REVIEW
    assert (
        len(
            {
                initial.bundle.authority_bundle_id,
                invalidated.bundle.authority_bundle_id,
                corrected.bundle.authority_bundle_id,
            }
        )
        == 2
    )
    assert invalidated.decision.supersedes_decision_id == initial.decision.issuer_decision_id
    assert corrected.decision.supersedes_decision_id == invalidated.decision.issuer_decision_id
    with harness.sessions() as session:
        assert session.scalar(select(func.count()).select_from(AuthorityBundleRow)) == 2
        assert session.scalar(select(func.count()).select_from(IssuerDecisionRow)) == 3


def test_later_revocation_preserves_history_and_appends_review_required(database_context) -> None:
    harness = _kr_harness(database_context)
    initial = harness.engine.evaluate(_kr_request(harness))
    old = harness.evidence["iros_jurisdiction"]
    reference = f"iros-verified-original:{KR_JURIR_NO}:revocation"
    revocation = _evidence(
        policy=KR_IROS_COMPLETE_POLICY,
        document_kind="VERIFIED_CORPORATE_REGISTRY_EXTRACT_V1",
        document_reference=reference,
        document_group="iros-revocation",
        scope=AuthorityScope.LEGAL_JURISDICTION,
        role=AuthoritySubjectRole.KOREAN_REGISTERED_LEGAL_ENTITY,
        claim_field="registry.legal_entity_status",
        value={
            "corporate_registration_reference": KR_JURIR_NO,
            "entity_kind": "DOMESTIC_CORPORATION",
            "jurisdiction": "KR",
            "verification_reference": reference,
        },
        evidence_kind=AuthorityEvidenceKind.REVOCATION,
    )
    _persist_evidence(harness.repository, revocation, fetched_at=CURRENT_FETCHED_AT)
    relation = build_authority_evidence_relation(
        predecessor_evidence_id=old.evidence_id,
        successor_evidence_id=revocation.evidence_id,
        relation_type=AuthorityEvidenceRelationType.REVOKES,
        recorded_at=EVALUATED_AT,
        authority_effective_missing_reason=(AuthorityTimeMissingReason.NOT_SUPPLIED_BY_AUTHORITY),
    )
    seed_preadmitted_authority_snapshot(harness.sessions, relations=(relation,))

    harness.clock.value = EVALUATED_AT + timedelta(minutes=1)
    result = harness.engine.evaluate(_kr_request(harness))

    assert result.decision.decision_state == IssuerMachineDecisionState.REVIEW_REQUIRED
    assert "AUTHORITY_EVIDENCE_NOT_CURRENT_HEAD" in result.decision.reason_codes
    assert harness.repository.evidence(old.evidence_id) == old
    assert harness.repository.evidence(revocation.evidence_id) == revocation
    assert result.decision.supersedes_decision_id == initial.decision.issuer_decision_id


def test_duplicate_corp_code_claims_are_both_preserved_and_no_first_writer_wins(
    database_context,
) -> None:
    first = _kr_harness(database_context, label="kr_duplicate_a")
    first_ready = first.engine.evaluate(_kr_request(first))
    second = _kr_harness(database_context, label="kr_duplicate_b")
    second_result = second.engine.evaluate(_kr_request(second))

    assert first_ready.decision.decision_state == IssuerMachineDecisionState.READY_FOR_MANUAL_REVIEW
    assert second_result.decision.decision_state == IssuerMachineDecisionState.UNRESOLVED
    assert "IDENTIFIER_PROVIDER_SUBJECT_COLLISION" in second_result.decision.reason_codes
    with first.sessions() as session:
        first_leaf = IssuerAuthorityDecisionEngine._decision_leaf(session, first.provider_id)
        assert first_leaf is not None
        assert first_leaf.decision_state == IssuerMachineDecisionState.REVIEW_REQUIRED
        assert first_leaf.supersedes_decision_id == first_ready.decision.issuer_decision_id
        assert "IMPACTED_READY_INVALIDATED_IN_COLLISION_TRANSACTION" in first_leaf.reason_codes
        claims = session.scalars(
            select(AuthorityIdentifierClaimRow).where(
                AuthorityIdentifierClaimRow.normalized_identifier_value == KR_CORP_CODE
            )
        ).all()
        assert len(claims) == 2
        assert {claim.provider_security_identity_id for claim in claims} == {
            first.provider_id,
            second.provider_id,
        }


def test_duplicate_registrant_cik_claims_are_both_preserved(database_context) -> None:
    first = _us_harness(database_context, label="us_duplicate_a")
    first_ready = first.engine.evaluate(_us_request(first))
    second = _us_harness(database_context, label="us_duplicate_b")
    result = second.engine.evaluate(_us_request(second))

    assert result.decision.decision_state == IssuerMachineDecisionState.UNRESOLVED
    assert "IDENTIFIER_PROVIDER_SUBJECT_COLLISION" in result.decision.reason_codes
    with first.sessions() as session:
        first_leaf = IssuerAuthorityDecisionEngine._decision_leaf(session, first.provider_id)
        assert first_leaf is not None
        assert first_leaf.decision_state == IssuerMachineDecisionState.REVIEW_REQUIRED
        assert first_leaf.supersedes_decision_id == first_ready.decision.issuer_decision_id
        assert (
            session.scalar(
                select(func.count())
                .select_from(AuthorityIdentifierClaimRow)
                .where(AuthorityIdentifierClaimRow.normalized_identifier_value == US_CIK)
            )
            == 2
        )


@pytest.mark.parametrize("jurisdiction", [Jurisdiction.KR, Jurisdiction.US])
@pytest.mark.parametrize("reverse_start_order", [False, True])
def test_concurrent_duplicate_identifier_writers_leave_no_ready_leaf(
    database_context,
    jurisdiction: Jurisdiction,
    reverse_start_order: bool,
) -> None:
    if jurisdiction == Jurisdiction.KR:
        first = _kr_harness(database_context, label="kr_concurrent_duplicate_a")
        second = _kr_harness(database_context, label="kr_concurrent_duplicate_b")
        request_factory = _kr_request
    else:
        first = _us_harness(database_context, label="us_concurrent_duplicate_a")
        second = _us_harness(database_context, label="us_concurrent_duplicate_b")
        request_factory = _us_request
    release = Event()
    failures: list[BaseException] = []

    def evaluate(harness: _Harness) -> None:
        try:
            assert release.wait(timeout=2)
            harness.engine.evaluate(request_factory(harness))
        except BaseException as error:
            failures.append(error)

    harnesses = [first, second]
    if reverse_start_order:
        harnesses.reverse()
    workers = [Thread(target=evaluate, args=(harness,)) for harness in harnesses]
    for worker in workers:
        worker.start()
    release.set()
    for worker in workers:
        worker.join(timeout=10)

    assert all(not worker.is_alive() for worker in workers)
    assert not failures
    with first.sessions() as session:
        leaves = (
            IssuerAuthorityDecisionEngine._decision_leaf(session, first.provider_id),
            IssuerAuthorityDecisionEngine._decision_leaf(session, second.provider_id),
        )
        assert all(leaf is not None for leaf in leaves)
        assert {leaf.decision_state for leaf in leaves if leaf is not None} == {
            IssuerMachineDecisionState.UNRESOLVED,
            IssuerMachineDecisionState.REVIEW_REQUIRED,
        }
        assert all(
            leaf.decision_state != IssuerMachineDecisionState.READY_FOR_MANUAL_REVIEW
            for leaf in leaves
            if leaf is not None
        )
    assert _zero_snapshot(first.sessions)["verified"] == 0


def test_same_provider_contradictory_candidate_is_review_required(database_context) -> None:
    harness = _kr_harness(database_context)
    initial = harness.engine.evaluate(_kr_request(harness))
    alternate_code = "00126381"
    alternate_corp = _evidence(
        policy=OPENDART_CORP_CODE_POLICY,
        document_kind="CORP_CODE_XML_V1",
        document_reference=f"corp-code:{alternate_code}",
        document_group=f"corp-code-{alternate_code}",
        scope=AuthorityScope.ISSUER_REGULATORY_ID,
        role=AuthoritySubjectRole.DART_DISCLOSURE_FILER,
        claim_field="corp_list.corp.corp_code",
        value=alternate_code,
    )
    alternate_overview = _evidence(
        policy=OPENDART_COMPANY_OVERVIEW_POLICY,
        document_kind="COMPANY_OVERVIEW_JSON_V1",
        document_reference=f"company-overview:{alternate_code}",
        document_group=f"company-overview-{alternate_code}",
        scope=AuthorityScope.LEGAL_ENTITY_BRIDGE,
        role=AuthoritySubjectRole.DART_DISCLOSURE_FILER,
        claim_field="company.identity_bridge",
        value={
            "corp_code": alternate_code,
            "jurir_no": KR_JURIR_NO,
            "stock_code": KR_SYMBOL,
        },
    )
    _persist_evidence(harness.repository, alternate_corp, fetched_at=HISTORICAL_FETCHED_AT)
    _persist_evidence(harness.repository, alternate_overview, fetched_at=CURRENT_FETCHED_AT)
    evidence_ids = (
        alternate_corp.evidence_id,
        alternate_overview.evidence_id,
        harness.evidence["iros_jurisdiction"].evidence_id,
        harness.evidence["iros_bridge"].evidence_id,
    )
    result = harness.engine.evaluate(
        _kr_request(
            harness,
            identifier_value=alternate_code,
            evidence_ids=evidence_ids,
        )
    )

    assert initial.decision.decision_state == IssuerMachineDecisionState.READY_FOR_MANUAL_REVIEW
    assert result.decision.decision_state == IssuerMachineDecisionState.REVIEW_REQUIRED
    assert "PROVIDER_CONTRADICTORY_ISSUER_CANDIDATES" in result.decision.reason_codes


def test_same_provider_contradictory_registrant_cik_is_review_required(
    database_context,
) -> None:
    harness = _us_harness(database_context)
    harness.engine.evaluate(_us_request(harness))
    alternate_cik = "0000320193"
    alternate_accession = "0000320193-26-000001"
    filing_group = f"sec-filing-{alternate_accession}"
    facts = (
        _evidence(
            policy=SEC_ACCEPTED_FILING_POLICY,
            document_kind="SEC_ACCEPTED_ISSUER_FILING_JSON_V1",
            document_reference=alternate_accession,
            document_group=filing_group,
            scope=AuthorityScope.ISSUER_REGULATORY_ID,
            role=AuthoritySubjectRole.SEC_REGISTRANT,
            claim_field="filing.registrant_cik",
            value=alternate_cik,
        ),
        _evidence(
            policy=SEC_ACCEPTED_FILING_POLICY,
            document_kind="SEC_ACCEPTED_ISSUER_FILING_JSON_V1",
            document_reference=alternate_accession,
            document_group=filing_group,
            scope=AuthorityScope.REGISTRANT_ROLE,
            role=AuthoritySubjectRole.SEC_REGISTRANT,
            claim_field="filing.registrant_role",
            value={
                "accepted_accession": alternate_accession,
                "registrant_cik": alternate_cik,
                "role": "ISSUER_REGISTRANT",
            },
        ),
        _evidence(
            policy=SEC_ACCEPTED_FILING_POLICY,
            document_kind="SEC_ACCEPTED_ISSUER_FILING_JSON_V1",
            document_reference=alternate_accession,
            document_group=filing_group,
            scope=AuthorityScope.LEGAL_ENTITY_BRIDGE,
            role=AuthoritySubjectRole.SEC_REGISTRANT,
            claim_field="filing.legal_entity_bridge",
            value={
                "accepted_accession": alternate_accession,
                "formation_state": "DE",
                "provider_symbol": US_SYMBOL,
                "registrant_cik": alternate_cik,
                "state_entity_number": US_STATE_ENTITY_NUMBER,
            },
        ),
        _evidence(
            policy=SEC_ACCEPTED_FILING_POLICY,
            document_kind="SEC_REGISTRANT_LATEST_STATUS_JSON_V1",
            document_reference="0000320193-26-000002",
            document_group=f"sec-latest-{alternate_cik}",
            scope=AuthorityScope.REGISTRANT_ROLE,
            role=AuthoritySubjectRole.SEC_REGISTRANT,
            claim_field="registrant.latest_filing_status",
            value={
                "latest_accession": "0000320193-26-000002",
                "registrant_cik": alternate_cik,
                "status": "CURRENT",
            },
        ),
    )
    for index, item in enumerate(facts):
        _persist_evidence(
            harness.repository,
            item,
            fetched_at=(HISTORICAL_FETCHED_AT if index < 3 else CURRENT_FETCHED_AT),
        )
    harness.clock.value = EVALUATED_AT + timedelta(minutes=1)
    request = build_issuer_authority_evaluation_request(
        provider_security_identity_id=harness.provider_id,
        provider_observation_ids=(harness.provider_observation_id,),
        candidate_jurisdiction=Jurisdiction.US,
        candidate_identifier_kind=AuthorityIdentifierKind.SEC_REGISTRANT_CIK,
        candidate_identifier_value=alternate_cik,
        evidence_ids=(
            *(item.evidence_id for item in facts),
            harness.evidence["state"].evidence_id,
        ),
    )

    result = harness.engine.evaluate(request)

    assert result.decision.decision_state == IssuerMachineDecisionState.REVIEW_REQUIRED
    assert "PROVIDER_CONTRADICTORY_ISSUER_CANDIDATES" in result.decision.reason_codes


def test_existing_canonical_identifier_conflict_blocks_ready_without_writing_canonical(
    database_context,
) -> None:
    harness = _kr_harness(database_context)
    with harness.sessions.begin() as session:
        session.add(
            IssuerRow(
                issuer_id="issuer_existing_conflicting_authority",
                jurisdiction="KR",
                corp_code=KR_CORP_CODE,
                cik=None,
                normalized_content_hash=authority_sha256({"existing": KR_CORP_CODE}),
                payload_json="{}",
            )
        )
    before = _zero_snapshot(harness.sessions)

    result = harness.engine.evaluate(_kr_request(harness))

    assert result.decision.decision_state == IssuerMachineDecisionState.UNRESOLVED
    assert "EXISTING_CANONICAL_IDENTIFIER_CONFLICT" in result.decision.reason_codes
    assert _zero_snapshot(harness.sessions) == before


def test_exact_same_deterministic_canonical_issuer_is_not_a_collision(
    database_context,
) -> None:
    harness = _kr_harness(database_context)
    issuer = _canonical_issuer(jurisdiction=Jurisdiction.KR, identifier_value=KR_CORP_CODE)
    _insert_canonical_issuer(harness.sessions, issuer)
    before = _zero_snapshot(harness.sessions)

    result = harness.engine.evaluate(_kr_request(harness))

    assert result.decision.decision_state == IssuerMachineDecisionState.READY_FOR_MANUAL_REVIEW
    assert "EXISTING_CANONICAL_IDENTIFIER_CONFLICT" not in result.decision.reason_codes
    assert _zero_snapshot(harness.sessions) == before


@pytest.mark.parametrize(
    ("stored_jurisdiction", "stored_corp_code"),
    [("US", KR_CORP_CODE), ("KR", "00126381")],
)
def test_same_canonical_issuer_id_with_contradictory_identity_is_a_collision(
    database_context,
    stored_jurisdiction: str,
    stored_corp_code: str,
) -> None:
    harness = _kr_harness(database_context)
    issuer = _canonical_issuer(jurisdiction=Jurisdiction.KR, identifier_value=KR_CORP_CODE)
    with harness.sessions.begin() as session:
        session.add(
            IssuerRow(
                issuer_id=issuer.issuer_id,
                jurisdiction=stored_jurisdiction,
                corp_code=stored_corp_code,
                cik=None,
                normalized_content_hash=issuer.normalized_content_hash,
                payload_json=issuer.model_dump_json(),
            )
        )
    before = _zero_snapshot(harness.sessions)

    result = harness.engine.evaluate(_kr_request(harness))

    assert result.decision.decision_state == IssuerMachineDecisionState.UNRESOLVED
    assert "EXISTING_CANONICAL_IDENTIFIER_CONFLICT" in result.decision.reason_codes
    assert _zero_snapshot(harness.sessions) == before


def test_arbitrary_active_provider_observation_membership_cannot_enable_ready(
    database_context,
) -> None:
    harness = _kr_harness(database_context)
    with harness.sessions() as session:
        identity = session.get(ProviderSecurityIdentityRow, harness.provider_id)
        assert identity is not None
        source_version_id = identity.latest_source_version_id
    collision_id = "tpsi_" + "f" * 64
    unsafe = build_security_master_observation(
        source_version_id=source_version_id,
        normalized_record_id=None,
        provider_security_identity_id=harness.provider_id,
        provider=ProviderSystem.TOSS_OPEN_API,
        market=Market.KR,
        symbol=KR_SYMBOL,
        name="Conflicting current provider observation",
        security_type=ProviderSecurityType.STOCK,
        is_common_share=True,
        isin=None,
        staging_state=ProviderSecurityMasterState.QUARANTINED,
        reconciliation_outcome=ProviderReconciliationOutcome.UNRESOLVED_COLLISION,
        identity_state_after=ProviderIdentityState.QUARANTINED,
        eligible_for_mapping=False,
        collision_identity_ids=(collision_id,),
        reason_codes=("CURRENT_PROVIDER_COLLISION",),
    )
    with harness.sessions.begin() as session:
        session.add(
            ProviderSecurityMasterObservationRow(
                observation_id=unsafe.observation_id,
                source_version_id=unsafe.source_version_id,
                normalized_record_id=unsafe.normalized_record_id,
                provider_security_identity_id=unsafe.provider_security_identity_id,
                provider=unsafe.provider.value,
                market=unsafe.market.value,
                symbol=unsafe.symbol,
                staging_state=unsafe.staging_state.value,
                reconciliation_outcome=unsafe.reconciliation_outcome.value,
                eligible_for_mapping=int(unsafe.eligible_for_mapping),
                provider_contract_version=unsafe.provider_contract_version,
                payload_json=unsafe.model_dump_json(),
            )
        )
    request = build_issuer_authority_evaluation_request(
        provider_security_identity_id=harness.provider_id,
        provider_observation_ids=(harness.provider_observation_id,),
        candidate_jurisdiction=Jurisdiction.KR,
        candidate_identifier_kind=AuthorityIdentifierKind.DART_CORP_CODE,
        candidate_identifier_value=KR_CORP_CODE,
        evidence_ids=tuple(item.evidence_id for item in harness.evidence.values()),
    )

    result = harness.engine.evaluate(request)

    assert result.decision.decision_state == IssuerMachineDecisionState.UNRESOLVED
    assert unsafe.observation_id not in request.provider_observation_ids
    assert "PROVIDER_OBSERVATION_NOT_BRIDGE_ELIGIBLE" in result.decision.reason_codes


def test_parser_cannot_raise_weight_or_relax_access_policy(database_context) -> None:
    harness = _kr_harness(database_context)
    overview = harness.evidence["overview"]
    values = overview.model_dump(mode="python")
    for computed in ("evidence_id", "evidence_content_hash", "evidence_provenance_hash"):
        values.pop(computed)
    values["policy_maximum_issuer_authority_weight"] = AuthorityWeight.DECISIVE
    raised_weight = build_authority_evidence(**values)
    values["policy_maximum_issuer_authority_weight"] = AuthorityWeight.SUPPORTING
    values["access_disposition"] = AuthorityAccessDisposition.RESTRICTED
    restricted = build_authority_evidence(**values)
    values["access_disposition"] = AuthorityAccessDisposition.PERMITTED
    values["license_disposition"] = AuthorityLicenseDisposition.RESTRICTED
    restricted_license = build_authority_evidence(**values)

    with pytest.raises(AuthorityLedgerConflict, match="exact source policy"):
        harness.repository.insert_or_verify_evidence(raised_weight)
    with pytest.raises(AuthorityLedgerConflict, match="exact source policy"):
        harness.repository.insert_or_verify_evidence(restricted)
    with pytest.raises(AuthorityLedgerConflict, match="exact source policy"):
        harness.repository.insert_or_verify_evidence(restricted_license)


def test_opendart_corp_class_cannot_be_relabelled_as_jurisdiction(database_context) -> None:
    harness = _kr_harness(database_context)
    invalid = _evidence(
        policy=OPENDART_COMPANY_OVERVIEW_POLICY,
        document_kind="COMPANY_OVERVIEW_JSON_V1",
        document_reference=f"company-overview:{KR_CORP_CODE}",
        document_group="company-overview-corp-cls",
        scope=AuthorityScope.LEGAL_JURISDICTION,
        role=AuthoritySubjectRole.DART_DISCLOSURE_FILER,
        claim_field="company.corp_cls",
        value="Y",
    )

    with pytest.raises(AuthorityLedgerConflict, match="exact source policy"):
        harness.repository.insert_or_verify_evidence(invalid)


def test_raw_normalized_mismatch_cannot_enter_positive_application(database_context) -> None:
    harness = _kr_harness(database_context)
    overview = harness.evidence["overview"]
    values = overview.model_dump(mode="python")
    for computed in ("evidence_id", "evidence_content_hash", "evidence_provenance_hash"):
        values.pop(computed)
    values["raw_claim_value"] = {
        "corp_code": KR_CORP_CODE,
        "jurir_no": KR_JURIR_NO,
        "stock_code": "000000",
    }
    mismatched = build_authority_evidence(**values)
    _persist_evidence(harness.repository, mismatched, fetched_at=CURRENT_FETCHED_AT)
    evidence_ids = tuple(
        mismatched.evidence_id if key == "overview" else item.evidence_id
        for key, item in harness.evidence.items()
    )

    result = harness.engine.evaluate(_kr_request(harness, evidence_ids=evidence_ids))

    assert result.decision.decision_state == IssuerMachineDecisionState.UNRESOLVED
    mismatched_application = next(
        application
        for application in result.applications
        if application.evidence_id == mismatched.evidence_id
    )
    assert (
        mismatched_application.application_status
        == AuthorityEvidenceApplicationStatus.REJECTED_UNUSABLE
    )
    assert mismatched_application.effective_issuer_authority_weight == AuthorityWeight.ZERO


def test_generic_us_state_registry_wildcard_policy_is_invalid() -> None:
    with pytest.raises(ValidationError, match="source_namespace"):
        build_authority_source_policy(
            source_namespace="US_STATE_REGISTRY_*",
            field_owner="Generic state registry",
            authority_classification=AuthorityClassification.OFFICIAL_AUTHORITY,
            allowed_document_kinds=("VERIFIED_DOMESTIC_ENTITY_RECORD_V1",),
            credential_free_locator_roots=("authority-verification://generic-state/",),
            scope_role_weights=(
                AuthorityScopeRoleWeight(
                    authority_scope=AuthorityScope.LEGAL_JURISDICTION,
                    subject_role=AuthoritySubjectRole.US_STATE_REGISTERED_LEGAL_ENTITY,
                    maximum_weight=AuthorityWeight.DECISIVE,
                ),
            ),
            ingestion_mode=AuthorityIngestionMode.HUMAN_ASSISTED_VERIFIED_DOCUMENT,
            admitted_adapter_contract_versions=("generic-state/0.1.0",),
            admitted_parser_contract_versions=("generic-state-parser/0.1.0",),
            production_authority_eligible=True,
            required_access_disposition=AuthorityAccessDisposition.PERMITTED,
            required_license_disposition=AuthorityLicenseDisposition.PERMITTED,
            allowed_origin_data_modes=(AuthorityOriginDataMode.PRODUCTION_AUTHORITY,),
            permanent_fixture_test_taint=False,
            registered_at=EVALUATED_AT,
        )


@pytest.mark.parametrize(
    "role",
    [AuthoritySubjectRole.SEC_LOGIN_CIK, AuthoritySubjectRole.SEC_FILING_AGENT],
)
def test_login_agent_and_accession_prefix_cannot_become_registrant(
    database_context,
    role: AuthoritySubjectRole,
) -> None:
    harness = _us_harness(database_context)
    seed_preadmitted_authority_snapshot(
        harness.sessions,
        policies=(SEC_LOGIN_PROVENANCE_POLICY,),
    )
    provenance_only_cik = "0000320193"
    provenance_accession = "0000320193-26-000001"
    provenance = _evidence(
        policy=SEC_LOGIN_PROVENANCE_POLICY,
        document_kind="SEC_SUBMISSION_PROVENANCE_JSON_V1",
        document_reference=provenance_accession,
        document_group=f"sec-provenance-{role.value}",
        scope=AuthorityScope.SUBMISSION_PROVENANCE,
        role=role,
        claim_field="submission.provenance_cik",
        value=provenance_only_cik,
        evidence_kind=AuthorityEvidenceKind.PROVENANCE_ONLY,
    )
    _persist_evidence(harness.repository, provenance, fetched_at=CURRENT_FETCHED_AT)

    result = harness.engine.evaluate(
        _us_request(
            harness,
            identifier_value=provenance_only_cik,
            evidence_ids=(provenance.evidence_id,),
        )
    )

    assert result.decision.decision_state == IssuerMachineDecisionState.UNRESOLVED
    assert not result.identifier_claims


def test_format_valid_unproven_cik_and_phase_one_synthetic_cik_fail_closed(
    database_context,
) -> None:
    harness = _us_harness(database_context)
    unproven = harness.engine.evaluate(
        _us_request(harness, identifier_value="0000123456", evidence_ids=())
    )

    assert unproven.decision.decision_state == IssuerMachineDecisionState.UNRESOLVED
    with pytest.raises(IssuerAuthorityDecisionEngineError, match="SYNTHETIC"):
        harness.engine.evaluate(
            _us_request(harness, identifier_value="9999999999", evidence_ids=())
        )


def test_listing_market_and_opendart_fields_never_supply_legal_jurisdiction(
    database_context,
) -> None:
    kr = _kr_harness(database_context, include_iros=False, overview_mode="SYMBOL_ONLY")
    kr_result = kr.engine.evaluate(_kr_request(kr))

    assert kr_result.decision.decision_state == IssuerMachineDecisionState.UNRESOLVED
    assert "MISSING_KR_IROS_JURISDICTION" in kr_result.decision.reason_codes


def _row_values(row, table) -> dict[str, Any]:
    return {column.name: getattr(row, column.name) for column in table.columns}


def _competing_identifier_claim(
    harness: _Harness,
) -> tuple[Any, SQLiteAuthorityLedgerRepository]:
    evidence = harness.evidence["corp"]
    relation_head = IssuerAuthorityDecisionEngine._relation_head(evidence.evidence_id, ())
    application = build_authority_evidence_application(
        policy=OPENDART_CORP_CODE_POLICY,
        evidence=evidence,
        provider_security_identity_id=harness.provider_id,
        provider_observation_ids=(harness.provider_observation_id,),
        candidate_jurisdiction=Jurisdiction.KR,
        candidate_identifier_kind=AuthorityIdentifierKind.DART_CORP_CODE,
        candidate_identifier_value=KR_CORP_CODE,
        claim_target_field="issuer.corp_code",
        requested_status=AuthorityEvidenceApplicationStatus.APPLIED_DECISIVE,
        requested_effective_weight=AuthorityWeight.DECISIVE,
        reason_codes=("EXACT_ENGINE_MATRIX_MATCH",),
        authority_relation_head_hash=relation_head.content_hash,
        evaluated_at=EVALUATED_AT,
    )
    harness.repository.insert_or_verify_evidence_application(application)
    claim = build_authority_identifier_claim(
        identifier_kind=AuthorityIdentifierKind.DART_CORP_CODE,
        normalized_identifier_value=KR_CORP_CODE,
        candidate_jurisdiction=Jurisdiction.KR,
        provider_security_identity_id=harness.provider_id,
        application=application,
        evidence=evidence,
        policy=OPENDART_CORP_CODE_POLICY,
        claim_role=AuthoritySubjectRole.DART_DISCLOSURE_FILER,
        recorded_at=EVALUATED_AT,
    )
    return claim, harness.repository


def test_current_positive_application_without_claim_still_blocks_ready(
    database_context,
) -> None:
    first = _kr_harness(database_context, label="kr_application_scan_first")
    second = _kr_harness(database_context, label="kr_application_scan_second")
    _competing_identifier_claim(second)
    before = _zero_snapshot(first.sessions)

    result = first.engine.evaluate(_kr_request(first))

    assert result.decision.decision_state == IssuerMachineDecisionState.UNRESOLVED
    assert "APPLICATION_IDENTIFIER_PROVIDER_COLLISION" in result.decision.reason_codes
    assert _zero_snapshot(first.sessions) == before


def test_collision_inserted_by_competing_writer_is_seen_before_ready_recheck(
    database_context,
) -> None:
    first = _kr_harness(database_context, label="kr_concurrency_first")
    first.engine.evaluate(_kr_request(first))
    second = _kr_harness(database_context, label="kr_concurrency_second")
    claim, repository = _competing_identifier_claim(second)
    claim_row = repository._identifier_claim_row(claim, claim.model_dump_json())
    started = Event()
    finished = Event()
    results: list[Any] = []
    failures: list[BaseException] = []

    def evaluate_after_lock() -> None:
        started.set()
        try:
            results.append(first.engine.evaluate(_kr_request(first)))
        except BaseException as error:
            failures.append(error)
        finally:
            finished.set()

    with database_context.engine.connect() as connection:
        connection.exec_driver_sql("BEGIN IMMEDIATE")
        worker = Thread(target=evaluate_after_lock)
        worker.start()
        assert started.wait(timeout=2)
        assert not finished.wait(timeout=0.1)
        connection.execute(
            AuthorityIdentifierClaimRow.__table__.insert(),
            _row_values(claim_row, AuthorityIdentifierClaimRow.__table__),
        )
        connection.commit()
        worker.join(timeout=5)

    assert not worker.is_alive()
    assert not failures
    assert results[0].decision.decision_state == IssuerMachineDecisionState.REVIEW_REQUIRED
    assert "IDENTIFIER_PROVIDER_SUBJECT_COLLISION" in results[0].decision.reason_codes


def test_relation_inserted_by_competing_writer_is_seen_before_ready_recheck(
    database_context,
) -> None:
    harness = _kr_harness(database_context, label="kr_relation_concurrency")
    harness.engine.evaluate(_kr_request(harness))
    old = harness.evidence["iros_jurisdiction"]
    reference = f"iros-verified-original:{KR_JURIR_NO}:concurrent-revocation"
    revocation = _evidence(
        policy=KR_IROS_COMPLETE_POLICY,
        document_kind="VERIFIED_CORPORATE_REGISTRY_EXTRACT_V1",
        document_reference=reference,
        document_group="iros-concurrent-revocation",
        scope=AuthorityScope.LEGAL_JURISDICTION,
        role=AuthoritySubjectRole.KOREAN_REGISTERED_LEGAL_ENTITY,
        claim_field="registry.legal_entity_status",
        value={
            "corporate_registration_reference": KR_JURIR_NO,
            "entity_kind": "DOMESTIC_CORPORATION",
            "jurisdiction": "KR",
            "verification_reference": reference,
        },
        evidence_kind=AuthorityEvidenceKind.REVOCATION,
    )
    _persist_evidence(harness.repository, revocation, fetched_at=CURRENT_FETCHED_AT)
    relation = build_authority_evidence_relation(
        predecessor_evidence_id=old.evidence_id,
        successor_evidence_id=revocation.evidence_id,
        relation_type=AuthorityEvidenceRelationType.REVOKES,
        recorded_at=EVALUATED_AT,
        authority_effective_missing_reason=(AuthorityTimeMissingReason.NOT_SUPPLIED_BY_AUTHORITY),
    )
    relation_row = harness.repository._relation_row(relation, relation.model_dump_json())
    started = Event()
    finished = Event()
    results: list[Any] = []
    failures: list[BaseException] = []

    def evaluate_after_lock() -> None:
        started.set()
        try:
            results.append(harness.engine.evaluate(_kr_request(harness)))
        except BaseException as error:
            failures.append(error)
        finally:
            finished.set()

    with database_context.engine.connect() as connection:
        connection.exec_driver_sql("BEGIN IMMEDIATE")
        worker = Thread(target=evaluate_after_lock)
        worker.start()
        assert started.wait(timeout=2)
        assert not finished.wait(timeout=0.1)
        connection.execute(
            AuthorityEvidenceRelationRow.__table__.insert(),
            _row_values(relation_row, AuthorityEvidenceRelationRow.__table__),
        )
        connection.commit()
        worker.join(timeout=5)

    assert not worker.is_alive()
    assert not failures
    assert results[0].decision.decision_state == IssuerMachineDecisionState.REVIEW_REQUIRED
    assert "AUTHORITY_EVIDENCE_NOT_CURRENT_HEAD" in results[0].decision.reason_codes
