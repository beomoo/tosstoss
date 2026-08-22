from typing import Self

from pydantic import NonNegativeInt, model_validator

from toss_dashboard_api.contracts.base import (
    NonEmptyText,
    NormalizedRecord,
    SafeId,
    UtcDatetime,
    validate_safe_locator,
)
from toss_dashboard_api.contracts.enums import (
    AvailabilityStatus,
    FinalityStatus,
    FreshnessStatus,
    RevisionStatus,
    SourceSystem,
)


class DataQualityStatus(NormalizedRecord):
    quality_status_id: SafeId
    issuer_id: SafeId
    source_system: SourceSystem
    dataset: NonEmptyText
    availability_status: AvailabilityStatus
    last_attempt_at: UtcDatetime
    last_success_at: UtcDatetime | None
    last_observed_at: UtcDatetime | None
    freshness_evaluated_at: UtcDatetime
    freshness_status: FreshnessStatus
    finality_status: FinalityStatus
    revision_status: RevisionStatus
    source_record_id: SafeId | None
    source_locator: NonEmptyText
    error_code: NonEmptyText | None
    error_message: NonEmptyText | None
    records_received: NonNegativeInt
    records_rejected: NonNegativeInt
    quality_flags: list[NonEmptyText]

    @model_validator(mode="after")
    def validate_quality_state(self) -> Self:
        self.require_missing_reasons(
            "last_success_at",
            "last_observed_at",
            "error_code",
            "error_message",
            "source_record_id",
        )
        validate_safe_locator(self.source_locator)
        if self.availability_status == AvailabilityStatus.ERROR and self.error_code is None:
            raise ValueError("ERROR status requires error_code")
        if (
            self.availability_status
            in {
                AvailabilityStatus.AVAILABLE,
                AvailabilityStatus.DEGRADED,
            }
            and self.last_success_at is None
        ):
            raise ValueError("available or degraded status requires last_success_at")
        if self.last_success_at and self.last_success_at > self.last_attempt_at:
            raise ValueError("last_success_at must not be after last_attempt_at")
        return self
