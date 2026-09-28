"""Fixed localhost WebAuthn verification, with strict original-byte boundaries."""

from __future__ import annotations

import hashlib
import hmac
import io
from dataclasses import dataclass, field
from typing import Any, NoReturn
from uuid import UUID

import cbor2
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from webauthn import verify_authentication_response, verify_registration_response
from webauthn.helpers.cose import COSEAlgorithmIdentifier

from .canonical import (
    ORIGIN,
    RP_ID,
    ReviewerError,
    base64url,
    decode_base64url,
    digest,
    strict_json,
    user_handle,
)


@dataclass(frozen=True, repr=False)
class PublicMaterial:
    credential_id: str
    credential_fingerprint: str
    cose: bytes
    key_fingerprint: str
    algorithm: str
    aaguid: str | None
    transports: tuple[str, ...]
    sign_count: int
    cred_props_rk: bool | None


@dataclass(repr=False)
class VerificationFacts:
    """Internal facts populated by checks, never deserialized from caller data."""

    flags: dict[str, int] = field(
        default_factory=lambda: {
            name: 0
            for name in (
                "client_data_type_verified",
                "challenge_verified",
                "origin_verified",
                "cross_origin_false_verified",
                "rp_id_hash_verified",
                "user_presence_verified",
                "user_verification_verified",
                "platform_authenticator_verified",
                "resident_key_verified",
                "public_key_material_verified",
                "credential_id_verified",
                "signature_verified",
                "counter_verified",
                "replay_rejected",
            )
        }
    )
    terminal_result: str = "SUCCEEDED"
    safe_code: str = "AUTHENTICATION_VERIFIED"
    user_handle_status: str = "NOT_EVALUATED"
    asserted_count: int | None = None
    material: PublicMaterial | None = None
    credential_id: str | None = None

    def reject(self, result: str, code: str) -> NoReturn:
        self.terminal_result = result
        self.safe_code = code
        raise ReviewerError(code)


def _cbor_item(raw: bytes) -> tuple[Any, int]:
    try:
        stream = io.BytesIO(raw)
        value = cbor2.CBORDecoder(stream, allow_duplicate_keys=False).decode()
        return value, stream.tell()
    except (ValueError, TypeError, cbor2.CBORDecodeError, RecursionError):
        raise ReviewerError("INVALID_CBOR") from None


def validate_cose(raw: bytes) -> tuple[str, Any]:
    """Only the two exact ADR-017 maps; equality rejects alternate encodings."""
    if len(raw) > 16_384 or not raw or raw[0] not in (0xA4, 0xA5):
        raise ReviewerError("INVALID_COSE")
    value, consumed = _cbor_item(raw)
    if consumed != len(raw) or type(value) is not dict:
        raise ReviewerError("INVALID_COSE")
    if any(type(key) is not int for key in value):
        raise ReviewerError("INVALID_COSE")
    if type(value.get(3)) is not int:
        raise ReviewerError("INVALID_COSE")
    public: ec.EllipticCurvePublicKey | rsa.RSAPublicKey
    try:
        if value.get(3) == -7 and set(value) == {1, 3, -1, -2, -3}:
            if (
                type(value[1]) is not int
                or value[1] != 2
                or type(value[-1]) is not int
                or value[-1] != 1
            ):
                raise ReviewerError("INVALID_COSE")
            if any(type(value[key]) is not bytes or len(value[key]) != 32 for key in (-2, -3)):
                raise ReviewerError("INVALID_COSE")
            public = ec.EllipticCurvePublicNumbers(
                int.from_bytes(value[-2], "big"), int.from_bytes(value[-3], "big"), ec.SECP256R1()
            ).public_key()
            algorithm = "ES256"
        elif value.get(3) == -257 and set(value) == {1, 3, -1, -2}:
            if type(value[1]) is not int or value[1] != 3:
                raise ReviewerError("INVALID_COSE")
            if any(
                type(value[key]) is not bytes or not value[key] or value[key][0] == 0
                for key in (-1, -2)
            ):
                raise ReviewerError("INVALID_COSE")
            modulus, exponent = int.from_bytes(value[-1], "big"), int.from_bytes(value[-2], "big")
            if (
                modulus.bit_length() < 2048
                or modulus % 2 != 1
                or exponent < 3
                or exponent % 2 != 1
                or exponent >= modulus
            ):
                raise ReviewerError("INVALID_COSE")
            public = rsa.RSAPublicNumbers(exponent, modulus).public_key()
            algorithm = "RS256"
        else:
            raise ReviewerError("INVALID_COSE")
        # Generic canonical CBOR is NOT a general CTAP2 encoder. These maps have
        # only the exact integer labels above; their ordering agrees with CTAP2.
        encoded = cbor2.dumps(value, canonical=True)
        if encoded != raw or cbor2.loads(encoded) != value:
            raise ReviewerError("NONCANONICAL_COSE")
        return algorithm, public
    except (ValueError, TypeError, OverflowError):
        raise ReviewerError("INVALID_COSE") from None


def _wire(payload: Any) -> dict[str, Any]:
    if type(payload) is not dict:
        raise ReviewerError("INVALID_CEREMONY")
    allowed = {
        "id",
        "rawId",
        "type",
        "response",
        "authenticatorAttachment",
        "clientExtensionResults",
    }
    if set(payload) - allowed or not {"id", "rawId", "type", "response"} <= set(payload):
        raise ReviewerError("UNTRUSTED_AUTHORITY_FIELD")
    if payload["type"] != "public-key" or type(payload["response"]) is not dict:
        raise ReviewerError("INVALID_CEREMONY")
    return payload


def _client(
    payload: dict[str, Any], expected_digest: str, kind: str, facts: VerificationFacts
) -> bytes:
    data = strict_json(decode_base64url(payload["response"].get("clientDataJSON")))
    if type(data) is not dict or data.get("type") != kind:
        facts.reject("BINDING_MISMATCH", "CLIENT_DATA_TYPE_MISMATCH")
    facts.flags["client_data_type_verified"] = 1
    raw = decode_base64url(data.get("challenge"))
    if len(raw) != 32 or not hmac.compare_digest(digest(raw), expected_digest):
        facts.reject("BINDING_MISMATCH", "CHALLENGE_MISMATCH")
    facts.flags["challenge_verified"] = 1
    if data.get("origin") != ORIGIN:
        facts.reject("ORIGIN_RP_MISMATCH", "ORIGIN_MISMATCH")
    facts.flags["origin_verified"] = 1
    if data.get("crossOrigin") is not False or "topOrigin" in data:
        facts.reject("ORIGIN_RP_MISMATCH", "CROSS_ORIGIN_REJECTED")
    facts.flags["cross_origin_false_verified"] = 1
    return raw


def _authenticator(raw: bytes, facts: VerificationFacts) -> int:
    if len(raw) < 37:
        facts.reject("FAILED_CLOSED", "INVALID_AUTHENTICATOR_DATA")
    if not hmac.compare_digest(raw[:32], hashlib.sha256(RP_ID.encode("ascii")).digest()):
        facts.reject("ORIGIN_RP_MISMATCH", "RP_ID_HASH_MISMATCH")
    facts.flags["rp_id_hash_verified"] = 1
    if not raw[32] & 1:
        facts.reject("USER_PRESENCE_ABSENT", "USER_PRESENCE_ABSENT")
    facts.flags["user_presence_verified"] = 1
    if not raw[32] & 4:
        facts.reject("USER_VERIFICATION_ABSENT", "USER_VERIFICATION_ABSENT")
    facts.flags["user_verification_verified"] = 1
    return int.from_bytes(raw[33:37], "big")


def registration_options(challenge: bytes, principal_id: str, operation_id: str) -> dict[str, Any]:
    return {
        "rp": {"id": RP_ID, "name": RP_ID},
        "user": {
            "id": base64url(user_handle(principal_id, operation_id)),
            "name": "local-data-steward",
            "displayName": "Local Data Steward",
        },
        "challenge": base64url(challenge),
        "pubKeyCredParams": [
            {"type": "public-key", "alg": -7},
            {"type": "public-key", "alg": -257},
        ],
        "timeout": 300_000,
        "attestation": "none",
        "authenticatorSelection": {
            "authenticatorAttachment": "platform",
            "residentKey": "required",
            "requireResidentKey": True,
            "userVerification": "required",
        },
        "extensions": {"credProps": True},
    }


def assertion_options(
    challenge: bytes, allowed: tuple[str, ...], timeout_ms: int
) -> dict[str, Any]:
    if not allowed or len(set(allowed)) != len(allowed):
        raise ReviewerError("EMPTY_OR_INVALID_ALLOW_CREDENTIALS")
    for credential_id in allowed:
        decode_base64url(credential_id)
    return {
        "rpId": RP_ID,
        "challenge": base64url(challenge),
        "timeout": timeout_ms,
        "userVerification": "required",
        "allowCredentials": [{"type": "public-key", "id": item} for item in allowed],
    }


def verify_registration(payload: Any, expected_digest: str) -> VerificationFacts:
    facts = VerificationFacts(safe_code="REGISTRATION_VERIFIED")
    try:
        wire = _wire(payload)
        if set(wire["response"]) - {
            "clientDataJSON",
            "attestationObject",
            "transports",
            "publicKey",
            "publicKeyAlgorithm",
            "authenticatorData",
        }:
            facts.reject("INVALID_REGISTRATION", "UNTRUSTED_AUTHORITY_FIELD")
        challenge = _client(wire, expected_digest, "webauthn.create", facts)
        credential_id = decode_base64url(wire["id"])
        if decode_base64url(wire["rawId"]) != credential_id:
            facts.reject("BINDING_MISMATCH", "CREDENTIAL_ID_MISMATCH")
        attestation_raw = decode_base64url(wire["response"].get("attestationObject"))
        attestation, used = _cbor_item(attestation_raw)
        if (
            used != len(attestation_raw)
            or type(attestation) is not dict
            or set(attestation) != {"fmt", "authData", "attStmt"}
        ):
            facts.reject("INVALID_REGISTRATION", "INVALID_ATTESTATION")
        auth_data = attestation["authData"]
        if type(auth_data) is not bytes:
            facts.reject("INVALID_REGISTRATION", "INVALID_AUTHENTICATOR_DATA")
        sign_count = _authenticator(auth_data, facts)
        if len(auth_data) < 55 or not auth_data[32] & 64:
            facts.reject("INVALID_REGISTRATION", "MISSING_ATTESTED_CREDENTIAL")
        length = int.from_bytes(auth_data[53:55], "big")
        offset = 55 + length
        if not length or offset >= len(auth_data) or auth_data[55:offset] != credential_id:
            facts.reject("BINDING_MISMATCH", "CREDENTIAL_ID_MISMATCH")
        _key, used = _cbor_item(auth_data[offset:])
        cose = auth_data[offset : offset + used]
        algorithm, _public = validate_cose(cose)
        result = verify_registration_response(
            credential=wire,
            expected_challenge=challenge,
            expected_rp_id=RP_ID,
            expected_origin=ORIGIN,
            require_user_presence=True,
            require_user_verification=True,
            supported_pub_key_algs=[
                COSEAlgorithmIdentifier.ECDSA_SHA_256,
                COSEAlgorithmIdentifier.RSASSA_PKCS1_v1_5_SHA_256,
            ],
        )
        if (
            result.credential_id != credential_id
            or result.credential_public_key != cose
            or result.sign_count != sign_count
        ):
            facts.reject("INVALID_REGISTRATION", "REGISTRATION_MATERIAL_MISMATCH")
        if wire.get("authenticatorAttachment") != "platform":
            facts.reject("INVALID_REGISTRATION", "PLATFORM_ATTACHMENT_REQUIRED")
        facts.flags["platform_authenticator_verified"] = 1
        extensions = wire.get("clientExtensionResults", {})
        if type(extensions) is not dict:
            facts.reject("INVALID_REGISTRATION", "INVALID_EXTENSION_RESULTS")
        props = extensions.get("credProps", {})
        if type(props) is not dict or ("rk" in props and props["rk"] is not True):
            facts.reject("INVALID_REGISTRATION", "RESIDENT_KEY_REQUIRED")
        facts.flags["resident_key_verified"] = 1
        facts.flags["public_key_material_verified"] = 1
        facts.flags["credential_id_verified"] = 1
        transports = wire["response"].get("transports", [])
        permitted = {"ble", "hybrid", "internal", "nfc", "smart-card", "usb"}
        if type(transports) is not list or any(
            type(item) is not str or item not in permitted for item in transports
        ):
            facts.reject("INVALID_REGISTRATION", "INVALID_TRANSPORT")
        facts.material = PublicMaterial(
            base64url(credential_id),
            digest(credential_id),
            cose,
            digest(cose),
            algorithm,
            str(UUID(bytes=auth_data[37:53])),
            tuple(sorted(set(transports))),
            sign_count,
            props.get("rk"),
        )
    except ReviewerError as error:
        if facts.terminal_result == "SUCCEEDED":
            facts.terminal_result, facts.safe_code = "INVALID_REGISTRATION", error.code
    except Exception:
        # Terminal rejection, never success or a partial authority write. Library
        # messages can contain untrusted origin/key material and are not propagated.
        facts.terminal_result, facts.safe_code = (
            "INVALID_REGISTRATION",
            "REGISTRATION_VERIFICATION_FAILED",
        )
    return facts


def verify_assertion(
    payload: Any,
    expected_digest: str,
    allowed: dict[str, tuple[bytes, bytes, int | None]],
    *,
    bootstrap: bool = False,
) -> VerificationFacts:
    facts = VerificationFacts()
    try:
        if not allowed:
            facts.reject("FAILED_CLOSED", "EMPTY_OR_INVALID_ALLOW_CREDENTIALS")
        wire = _wire(payload)
        if set(wire["response"]) - {
            "clientDataJSON",
            "authenticatorData",
            "signature",
            "userHandle",
        }:
            facts.reject("BINDING_MISMATCH", "UNTRUSTED_AUTHORITY_FIELD")
        challenge = _client(wire, expected_digest, "webauthn.get", facts)
        raw_id = decode_base64url(wire["id"])
        if decode_base64url(wire["rawId"]) != raw_id or wire["id"] not in allowed:
            facts.reject("BINDING_MISMATCH", "CREDENTIAL_ID_MISMATCH")
        facts.credential_id = wire["id"]
        facts.flags["credential_id_verified"] = 1
        cose, expected_handle, previous = allowed[wire["id"]]
        validate_cose(cose)
        returned_handle = wire["response"].get("userHandle")
        if returned_handle is not None:
            try:
                decoded_handle = decode_base64url(returned_handle)
            except ReviewerError:
                facts.user_handle_status = "MISMATCHED"
                facts.reject("BINDING_MISMATCH", "USER_HANDLE_MISMATCH")
            if not hmac.compare_digest(decoded_handle, expected_handle):
                facts.user_handle_status = "MISMATCHED"
                facts.reject("BINDING_MISMATCH", "USER_HANDLE_MISMATCH")
            facts.user_handle_status = "MATCHED"
        else:
            facts.user_handle_status = "ABSENT_ALLOWED"
        auth_data = decode_base64url(wire["response"].get("authenticatorData"))
        count = _authenticator(auth_data, facts)
        # A rejected audit may retain the observed, untrusted wire count. Only
        # signature_verified + the ledger policy can give that count authority.
        facts.asserted_count = count
        decode_base64url(wire["response"].get("signature"))
        # The high-level verifier supplies actual signature/RP/UP/UV validation.
        # A zero baseline lets it verify rollback signatures too; the real ledger
        # counter policy is enforced below, never replaced with this API baseline.
        try:
            result = verify_authentication_response(
                credential=wire,
                expected_challenge=challenge,
                expected_rp_id=RP_ID,
                expected_origin=ORIGIN,
                credential_public_key=cose,
                credential_current_sign_count=0,
                require_user_verification=True,
            )
        except Exception:
            facts.reject("INVALID_SIGNATURE", "ASSERTION_VERIFICATION_FAILED")
        if result.credential_id != raw_id or result.new_sign_count != count:
            facts.reject("BINDING_MISMATCH", "ASSERTION_MATERIAL_MISMATCH")
        facts.flags["signature_verified"] = 1
        facts.asserted_count = count
        if previous is not None and not bootstrap and count <= previous:
            facts.reject("COUNTER_REJECTED", "COUNTER_DID_NOT_ADVANCE")
        facts.flags["counter_verified"] = 1
    except ReviewerError as error:
        if facts.terminal_result == "SUCCEEDED":
            facts.terminal_result, facts.safe_code = "FAILED_CLOSED", error.code
    except Exception:
        facts.terminal_result, facts.safe_code = "FAILED_CLOSED", "INVALID_CEREMONY"
    return facts
