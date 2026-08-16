from typing import Annotated, Self

from pydantic import StringConstraints, field_validator, model_validator

from toss_dashboard_api.contracts.base import (
    NormalizedRecord,
    SafeId,
    Sha256,
    UtcDatetime,
    validate_safe_locator,
)
from toss_dashboard_api.contracts.enums import (
    FinalityStatus,
    FreshnessStatus,
    RevisionStatus,
    SourceSystem,
    SourceType,
)

OpaqueRef = Annotated[
    str, StringConstraints(pattern=r"^fixture-raw:[a-z0-9_./-]+$", max_length=256)
]


class SourceRecord(NormalizedRecord):
    source_record_id: SafeId
    source_system: SourceSystem
    source_type: SourceType
    external_id: Annotated[str, StringConstraints(min_length=1, max_length=128)]
    source_locator: Annotated[str, StringConstraints(min_length=1, max_length=2048)]
    observed_at: UtcDatetime
    published_at: UtcDatetime
    fetched_at: UtcDatetime
    freshness_status: FreshnessStatus
    finality_status: FinalityStatus
    revision_status: RevisionStatus
    supersedes_id: SafeId | None
    raw_content_hash: Sha256
    parser_version: Annotated[str, StringConstraints(pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$")]
    raw_storage_ref: OpaqueRef

    @field_validator("source_locator")
    @classmethod
    def source_locator_is_safe(cls, value: str) -> str:
        return validate_safe_locator(value)

    @model_validator(mode="after")
    def validate_revision(self) -> Self:
        if self.supersedes_id == self.source_record_id:
            raise ValueError("source record cannot supersede itself")
        if self.revision_status == RevisionStatus.AMENDED and self.supersedes_id is None:
            raise ValueError("amended source record requires supersedes_id")
        if self.revision_status == RevisionStatus.ORIGINAL and self.supersedes_id is not None:
            raise ValueError("original source record cannot supersede another record")
        return self
