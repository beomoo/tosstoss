"""ADR-017 canonical bytes. No caller payload is an authority record."""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
import unicodedata
from datetime import UTC, datetime, timedelta
from typing import Any

POLICY = "issuer-steward-webauthn/0.1.0"
ROLE = "LOCAL_DATA_STEWARD"
RP_ID = "localhost"
ORIGIN = "http://localhost:3000"
HANDLE_POLICY = "issuer-steward-webauthn-user-handle/0.1.0"


class ReviewerError(RuntimeError):
    """Safe typed failure: never include library exceptions or ceremony bytes."""

    def __init__(self, code: str) -> None:
        if re.fullmatch(r"[A-Z][A-Z0-9_]{0,127}", code) is None:
            code = "REVIEWER_FAILED_CLOSED"
        self.code = code
        super().__init__(code)


class LedgerCorruption(ReviewerError):
    def __init__(self) -> None:
        super().__init__("REVIEWER_LEDGER_CORRUPT")


def nfc(value: str) -> str:
    try:
        normalized = unicodedata.normalize("NFC", value)
        normalized.encode("utf-8", errors="strict")
        return normalized
    except (UnicodeError, TypeError):
        raise ReviewerError("INVALID_UNICODE") from None


def _normalized(value: Any) -> Any:
    if value is None or type(value) in (bool, int):
        return value
    if type(value) is str:
        return nfc(value)
    if type(value) is list:
        return [_normalized(item) for item in value]
    if type(value) is dict:
        result: dict[str, Any] = {}
        for key, item in value.items():
            if type(key) is not str:
                raise ReviewerError("INVALID_JSON_KEY")
            key = nfc(key)
            if key in result:
                raise ReviewerError("DUPLICATE_JSON_KEY")
            result[key] = _normalized(item)
        return {key: result[key] for key in sorted(result, key=lambda key: key.encode("utf-8"))}
    raise ReviewerError("INVALID_JSON_VALUE")


def canonical_json(value: Any) -> bytes:
    try:
        return json.dumps(
            _normalized(value), ensure_ascii=False, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    except (ValueError, RecursionError):
        raise ReviewerError("INVALID_JSON_VALUE") from None


def digest(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def content_hash(value: Any) -> str:
    return digest(canonical_json(value))


def base64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def decode_base64url(value: Any, *, nonempty: bool = True) -> bytes:
    if type(value) is not str or len(value) > 1_048_576:
        raise ReviewerError("INVALID_BASE64URL")
    if (nonempty and not value) or re.fullmatch(r"[A-Za-z0-9_-]*", value) is None:
        raise ReviewerError("INVALID_BASE64URL")
    try:
        raw = base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True)
    except (ValueError, binascii.Error):
        raise ReviewerError("INVALID_BASE64URL") from None
    if base64url(raw) != value:
        raise ReviewerError("INVALID_BASE64URL")
    return raw


def strict_json(raw: bytes | str) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            normalized = nfc(key)
            if normalized in result:
                raise ReviewerError("DUPLICATE_JSON_KEY")
            result[normalized] = value
        return result

    def forbidden(_value: str) -> Any:
        raise ReviewerError("INVALID_JSON_VALUE")

    try:
        if len(raw) > 1_048_576:
            raise ReviewerError("INVALID_JSON_VALUE")
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="strict")
        return json.loads(
            raw, object_pairs_hook=pairs, parse_float=forbidden, parse_constant=forbidden
        )
    except (ValueError, UnicodeError, RecursionError):
        raise ReviewerError("INVALID_JSON_VALUE") from None


def utc_text(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ReviewerError("INVALID_SERVER_TIME")
    return value.isoformat(timespec="microseconds" if value.microsecond else "seconds").replace(
        "+00:00", "Z"
    )


def parse_utc(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
        if utc_text(parsed) != value:
            raise ReviewerError("INVALID_SERVER_TIME")
        return parsed
    except (TypeError, ValueError):
        raise ReviewerError("INVALID_SERVER_TIME") from None


def server_now() -> datetime:
    return datetime.now(UTC)


def challenge_expiry(issued: datetime, *, parent_expiry: datetime | None = None) -> datetime:
    utc_text(issued)
    result = issued + timedelta(minutes=5)
    if parent_expiry is not None:
        utc_text(parent_expiry)
        result = min(result, parent_expiry)
    if result <= issued:
        raise ReviewerError("EXPIRED")
    return result


def user_handle(principal_id: str, registering_operation_id: str) -> bytes:
    return hashlib.sha256(
        HANDLE_POLICY.encode("ascii")
        + b"\0"
        + nfc(principal_id).encode("utf-8")
        + b"\0"
        + nfc(registering_operation_id).encode("utf-8")
    ).digest()


# Exhaustive fields, independent of dict order, ORM repr, and database introspection.
PRINCIPAL_FIELDS = """contract_version enrollment_policy_version os_owner_sid_hash
principal_state reviewer_principal_id reviewer_role""".split()
CREDENTIAL_FIELDS = """authenticator_aaguid authenticator_attachment authenticator_transports
contract_version cose_public_key_canonical counter_capability credential_id_fingerprint
principal_content_hash public_key_algorithm public_key_fingerprint registration_policy_version
registration_sign_count resident_key_required reviewer_principal_id reviewer_role rp_id
user_verification_required webauthn_credential_id""".split()
OPERATION_FIELDS = """contract_version reviewer_principal_id reviewer_role principal_content_hash
os_owner_sid_hash operation_type target_webauthn_credential_id target_credential_id_fingerprint
expected_credential_state_hash initial_challenge_id initial_challenge_purpose
predecessor_operation_id
operation_policy_version""".split()
CHALLENGE_FIELDS = """allowed_origin authentication_policy_version challenge_digest
challenge_nonce_length challenge_purpose client_data_type contract_version
expected_credential_state_hash
expires_at issued_at operation_content_hash operation_type os_owner_sid_hash
platform_attachment_required prerequisite_authentication_content_hash
prerequisite_authentication_event_id
prerequisite_authentication_result principal_content_hash resident_key_required
reviewer_credential_operation_challenge_id reviewer_credential_operation_id reviewer_principal_id
reviewer_role rp_id target_credential_id_fingerprint target_webauthn_credential_id
user_verification_required""".split()
CONSUMPTION_FIELDS = """contract_version reviewer_credential_operation_challenge_id
reviewer_credential_operation_id reviewer_principal_id operation_type challenge_purpose
challenge_binding_hash terminal_result safe_result_code client_data_type_verified challenge_verified
origin_verified cross_origin_false_verified rp_id_hash_verified user_presence_verified
user_verification_verified platform_authenticator_verified resident_key_verified
public_key_material_verified registered_webauthn_credential_id registered_credential_content_hash
registered_credential_id_fingerprint registered_public_key_fingerprint registered_rp_id
registered_counter_capability registered_sign_count terminal_operation_outcome_id
terminal_operation_outcome_result outcome_expected_credential_state_hash
outcome_resulting_credential_state_hash continuation_challenge_id
continuation_challenge_purpose""".split()
AUTHENTICATION_FIELDS = """asserted_sign_count authentication_policy_version authentication_result
authorizing_webauthn_credential_id challenge_binding_hash challenge_consumption_content_hash
challenge_consumption_id challenge_purpose challenge_terminal_result contract_version
counter_capability
counter_verified credential_id_fingerprint exact_origin expected_credential_state_hash
operation_content_hash operation_type origin_verified os_owner_sid_hash previous_sign_count
principal_content_hash public_key_fingerprint replay_rejected
reviewer_credential_operation_challenge_id
reviewer_credential_operation_id reviewer_principal_id reviewer_role rp_id rp_id_hash_verified
safe_result_code signature_verified user_presence_verified user_verification_verified""".split()
EVENT_FIELDS = """contract_version event_type reviewer_principal_id structured_reason_code
supersedes_credential_event_id webauthn_credential_id""".split()
OUTCOME_FIELDS = """contract_version reviewer_credential_operation_id operation_content_hash
reviewer_principal_id reviewer_role principal_content_hash os_owner_sid_hash operation_type
terminal_result terminal_consumption_id terminal_consumption_content_hash terminal_challenge_purpose
terminal_challenge_result authorization_authentication_event_id
authorization_authentication_content_hash
authorization_authentication_result registration_consumption_id
registration_consumption_content_hash
registration_challenge_purpose registration_terminal_result expected_credential_state_hash
resulting_credential_state_hash safe_result_code""".split()
AUTHORIZATION_FIELDS = """credential_event_id contract_version credential_event_content_hash
webauthn_credential_id webauthn_credential_content_hash reviewer_principal_id reviewer_role
principal_content_hash os_owner_sid_hash event_type reviewer_credential_operation_id
operation_content_hash
operation_type authorization_kind registration_consumption_id registration_consumption_content_hash
registration_challenge_purpose registration_terminal_result
credential_operation_authentication_event_id
credential_operation_authentication_content_hash credential_operation_authentication_result
credential_operation_outcome_id credential_operation_outcome_content_hash
credential_operation_outcome_result
expected_credential_state_hash resulting_credential_state_hash""".split()
ISSUER_CHALLENGE_FIELDS = """allowed_origin authentication_policy_version authority_bundle_id
challenge_digest contract_version expected_bundle_content_hash
expected_decision_content_hash expires_at
issued_at issuer_approval_challenge_id issuer_decision_id predecessor_approval_event_id
predecessor_link_id
principal_content_hash proposed_issuer_id provider_security_identity_id requested_disposition
reviewer_principal_id reviewer_role rp_id successor_decision_id
user_verification_required""".split()
ISSUER_AUTHENTICATION_FIELDS = """asserted_sign_count authentication_policy_version
authentication_result
authority_bundle_id challenge_consumption_id contract_version counter_capability counter_verified
credential_id_fingerprint exact_origin expected_bundle_content_hash expected_decision_content_hash
issuer_approval_challenge_id issuer_decision_id origin_verified previous_sign_count
public_key_fingerprint
replay_rejected requested_disposition reviewer_principal_id reviewer_role rp_id rp_id_hash_verified
safe_result_code signature_verified user_presence_verified user_verification_verified
webauthn_credential_id""".split()
BOOLEAN_FIELDS = frozenset(
    """resident_key_required require_resident_key user_verification_required
platform_attachment_required cred_props_requested cred_props_rk client_data_type_verified
challenge_verified origin_verified cross_origin_false_verified rp_id_hash_verified
user_presence_verified user_verification_verified platform_authenticator_verified
resident_key_verified public_key_material_verified credential_id_verified signature_verified
counter_verified replay_rejected classification_verified""".split()
)


def row_preimage(row: dict[str, Any], fields: list[str]) -> dict[str, Any]:
    try:
        result = {field: row[field] for field in fields}
        for field in BOOLEAN_FIELDS.intersection(result):
            value = result[field]
            if value is not None:
                if type(value) not in (bool, int) or value not in (0, 1):
                    raise LedgerCorruption()
                result[field] = bool(value)
        return result
    except KeyError:
        raise LedgerCorruption() from None


def row_hash(row: dict[str, Any], fields: list[str]) -> str:
    return content_hash(row_preimage(row, fields))
