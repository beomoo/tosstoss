from typing import Protocol

from toss_dashboard_api.contracts.packet import AnalysisPacket
from toss_dashboard_api.contracts.provider_identity import (
    ProviderIdentifierHistory,
    ProviderIdentityMapping,
    ProviderLatestPointer,
    ProviderSecurityIdentity,
)
from toss_dashboard_api.contracts.provider_source import (
    CanonicalRequest,
    CollectionAttempt,
    ProviderAuditEvent,
    ProviderRawManifest,
    ProviderSourceVersion,
)
from toss_dashboard_api.contracts.quality import DataQualityStatus
from toss_dashboard_api.contracts.security import Security
from toss_dashboard_api.domain.overview import CompanyOverview
from toss_dashboard_api.repositories.provider import InsertResult


class MetadataRepository(Protocol):
    def list_securities(self) -> list[Security]: ...

    def issuer_exists(self, issuer_id: str) -> bool: ...

    def data_quality_for_issuer(self, issuer_id: str) -> list[DataQualityStatus]: ...

    def database_revision(self) -> str: ...

    def fixture_version(self) -> str | None: ...

    def fixture_manifest_digest(self) -> str | None: ...


class AnalyticsRepository(Protocol):
    def company_overview(self, issuer_id: str) -> CompanyOverview | None: ...

    def analysis_packet(self) -> AnalysisPacket | None: ...


class ProviderRepository(Protocol):
    def insert_or_verify_canonical_request(
        self, request: CanonicalRequest
    ) -> InsertResult[CanonicalRequest]: ...

    def insert_or_verify_raw_manifest(
        self, manifest: ProviderRawManifest
    ) -> InsertResult[ProviderRawManifest]: ...

    def append_source_version(
        self, version: ProviderSourceVersion
    ) -> InsertResult[ProviderSourceVersion]: ...

    def record_source_version_with_audit(
        self, version: ProviderSourceVersion, event: ProviderAuditEvent
    ) -> InsertResult[ProviderSourceVersion]: ...

    def source_revision_chain(self, source_version_id: str) -> list[ProviderSourceVersion]: ...

    def record_collection_attempt(
        self, attempt: CollectionAttempt
    ) -> InsertResult[CollectionAttempt]: ...

    def append_audit_event(self, event: ProviderAuditEvent) -> InsertResult[ProviderAuditEvent]: ...

    def insert_or_verify_identity(
        self, identity: ProviderSecurityIdentity
    ) -> InsertResult[ProviderSecurityIdentity]: ...

    def append_identifier_history(
        self, history: ProviderIdentifierHistory
    ) -> InsertResult[ProviderIdentifierHistory]: ...

    def record_identity_mapping(
        self, mapping: ProviderIdentityMapping
    ) -> InsertResult[ProviderIdentityMapping]: ...

    def read_latest_pointer(
        self, dataset: str, provider_security_identity_id: str
    ) -> ProviderLatestPointer | None: ...

    def conditional_write_latest(
        self, pointer: ProviderLatestPointer, *, expected_state_hash: str | None
    ) -> InsertResult[ProviderLatestPointer]: ...
