from typing import Self

from pydantic import model_validator

from toss_dashboard_api.contracts.base import (
    DecimalString,
    NonEmptyText,
    NormalizedRecord,
    SafeId,
    UtcDatetime,
)
from toss_dashboard_api.contracts.enums import (
    EvidenceBasis,
    EvidenceDirection,
    VerificationStatus,
)


class Evidence(NormalizedRecord):
    evidence_id: SafeId
    issuer_id: SafeId
    evidence_basis: EvidenceBasis
    verification_status: VerificationStatus
    direction: EvidenceDirection
    claim: NonEmptyText
    source_record_id: SafeId | None
    source_excerpt: NonEmptyText | None
    observed_at: UtcDatetime
    confidence: DecimalString

    @model_validator(mode="after")
    def validate_evidence(self) -> Self:
        self.require_missing_reasons("source_record_id", "source_excerpt")
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        if self.evidence_basis == EvidenceBasis.DIRECT_SOURCE and self.source_record_id is None:
            raise ValueError("direct evidence requires a source record")
        return self
