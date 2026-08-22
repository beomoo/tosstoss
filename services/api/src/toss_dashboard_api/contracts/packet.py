from __future__ import annotations

from pydantic import Field

from toss_dashboard_api.contracts.base import (
    NonEmptyText,
    NormalizedRecord,
    SafeId,
    Sha256,
    StrictContract,
    UtcDatetime,
)
from toss_dashboard_api.contracts.enums import SampleResult


class PacketSourceManifestEntry(StrictContract):
    source_record_id: SafeId
    raw_content_hash: Sha256


class PacketExtensions(StrictContract):
    extension_version: NonEmptyText
    hypotheses: list[dict[NonEmptyText, NonEmptyText]] = Field(default_factory=list)
    invalidation_conditions: list[dict[NonEmptyText, NonEmptyText]] = Field(default_factory=list)
    scenario_probability_changes: list[dict[NonEmptyText, NonEmptyText]] = Field(
        default_factory=list
    )


class AnalysisPacket(NormalizedRecord):
    packet_id: SafeId
    issuer_id: SafeId
    selected_security_id: SafeId
    generated_at: UtcDatetime
    evidence_ids: list[SafeId]
    input_data_ids: list[SafeId]
    source_manifest: list[PacketSourceManifestEntry]
    extensions: PacketExtensions
    result_status: SampleResult
