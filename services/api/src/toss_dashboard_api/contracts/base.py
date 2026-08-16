from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    PlainSerializer,
    StringConstraints,
    field_validator,
)

from toss_dashboard_api.contracts.enums import MissingReason

CONTRACT_VERSION = "0.1.0"
ContractVersion = Literal["0.1.0"]
HASH_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
DECIMAL_PATTERN = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")
ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]{2,127}$")
SafeId = Annotated[str, StringConstraints(pattern=ID_PATTERN.pattern, max_length=128)]
Sha256 = Annotated[str, StringConstraints(pattern=HASH_PATTERN.pattern)]


def decimal_to_string(value: Decimal) -> str:
    if not value.is_finite():
        raise ValueError("decimal must be finite")
    rendered = format(value, "f")
    return "0" if rendered in {"-0", "-0.0"} else rendered


def validate_decimal(value: object) -> Decimal:
    if isinstance(value, bool) or isinstance(value, int | float):
        raise ValueError("decimal JSON values must be canonical strings")
    if isinstance(value, Decimal):
        parsed = value
    elif isinstance(value, str) and DECIMAL_PATTERN.fullmatch(value):
        try:
            parsed = Decimal(value)
        except InvalidOperation as exc:
            raise ValueError("invalid decimal string") from exc
    else:
        raise ValueError("decimal must be a non-exponent string")
    if not parsed.is_finite():
        raise ValueError("decimal must be finite")
    return parsed


DecimalString = Annotated[
    Decimal,
    BeforeValidator(validate_decimal),
    PlainSerializer(decimal_to_string, return_type=str, when_used="json"),
]


def validate_utc_datetime(value: object) -> datetime:
    parsed: datetime
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        if not (value.endswith("Z") or re.search(r"[+-][0-9]{2}:[0-9]{2}$", value)):
            raise ValueError("timestamp must include a timezone")
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("invalid timestamp") from exc
    else:
        raise ValueError("timestamp must be an ISO 8601 string")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must include a timezone")
    return parsed.astimezone(UTC)


UtcDatetime = Annotated[datetime, BeforeValidator(validate_utc_datetime)]


def utc_to_string(value: datetime) -> str:
    normalized = value.astimezone(UTC).isoformat(
        timespec="microseconds" if value.microsecond else "seconds"
    )
    return normalized.replace("+00:00", "Z")


def canonical_json_bytes(value: Any) -> bytes:
    def default(item: object) -> object:
        if isinstance(item, Decimal):
            return decimal_to_string(item)
        if isinstance(item, datetime):
            return utc_to_string(item)
        raise TypeError(f"Unsupported canonical JSON value: {type(item).__name__}")

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
        default=default,
    ).encode("utf-8")


def sha256_prefixed(payload: bytes) -> str:
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def normalized_hash(value: BaseModel | dict[str, Any]) -> str:
    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else dict(value)
    payload.pop("normalized_content_hash", None)
    return sha256_prefixed(canonical_json_bytes(payload))


class StrictContract(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        validate_assignment=True,
        populate_by_name=False,
    )

    contract_version: ContractVersion
    missing_reasons: dict[str, MissingReason] = Field(default_factory=dict)

    @field_validator("missing_reasons")
    @classmethod
    def validate_missing_reason_keys(
        cls, value: dict[str, MissingReason]
    ) -> dict[str, MissingReason]:
        if any(not key or key.startswith("_") for key in value):
            raise ValueError("missing reason keys must be public field names")
        return value

    def require_missing_reasons(self, *field_names: str) -> None:
        for name in field_names:
            if getattr(self, name) is None and name not in self.missing_reasons:
                raise ValueError(f"missing_reasons.{name} is required when {name} is null")
            if getattr(self, name) is not None and name in self.missing_reasons:
                raise ValueError(f"missing_reasons.{name} is only allowed when {name} is null")


class NormalizedRecord(StrictContract):
    normalized_content_hash: Sha256


class ApiEnvelopeBase(StrictContract):
    data_mode: Literal["FIXTURE"]


def validate_safe_locator(value: str) -> str:
    lowered = value.lower()
    if lowered.startswith("https://") or lowered.startswith("fixture://"):
        return value
    raise ValueError("source locator must use https:// or fixture://")
