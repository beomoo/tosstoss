from datetime import date
from typing import Self

from pydantic import model_validator

from toss_dashboard_api.contracts.base import DecimalString, NormalizedRecord, SafeId, UtcDatetime
from toss_dashboard_api.contracts.enums import (
    FilingChangeType,
    FilingFormType,
    Jurisdiction,
    ReviewStatus,
    RevisionStatus,
    SampleResult,
)


class FilingDocument(NormalizedRecord):
    filing_id: SafeId
    issuer_id: SafeId
    jurisdiction: Jurisdiction
    form_type: FilingFormType
    period_end: date
    filed_at: UtcDatetime
    revision_status: RevisionStatus
    supersedes_filing_id: SafeId | None
    source_record_id: SafeId

    @model_validator(mode="after")
    def validate_revision(self) -> Self:
        if self.supersedes_filing_id == self.filing_id:
            raise ValueError("filing cannot supersede itself")
        if self.revision_status == RevisionStatus.AMENDED and self.supersedes_filing_id is None:
            raise ValueError("amended filing requires supersedes_filing_id")
        if (
            self.revision_status == RevisionStatus.ORIGINAL
            and self.supersedes_filing_id is not None
        ):
            raise ValueError("original filing cannot supersede another filing")
        return self


class FilingSentenceChange(NormalizedRecord):
    change_id: SafeId
    issuer_id: SafeId
    previous_filing_id: SafeId
    current_filing_id: SafeId
    section_key: str
    primary_change_type: FilingChangeType
    change_types: list[FilingChangeType]
    previous_sentence: str
    current_sentence: str
    semantic_similarity: DecimalString
    confidence: DecimalString
    rule_hits: list[str]
    review_status: ReviewStatus
    human_review_required: bool
    result_status: SampleResult

    @model_validator(mode="after")
    def validate_change(self) -> Self:
        if not self.change_types or self.primary_change_type not in self.change_types:
            raise ValueError("primary_change_type must be present in change_types")
        if len(set(self.change_types)) != len(self.change_types):
            raise ValueError("change_types must not contain duplicates")
        if not 0 <= self.semantic_similarity <= 1 or not 0 <= self.confidence <= 1:
            raise ValueError("similarity and confidence must be between 0 and 1")
        return self
