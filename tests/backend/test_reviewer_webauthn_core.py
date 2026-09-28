from __future__ import annotations

import re
import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import cbor2
import pytest
from tests.backend.reviewer_test_support import Authenticator

from toss_dashboard_api.reviewer import canonical as c
from toss_dashboard_api.reviewer.webauthn_core import (
    assertion_options,
    registration_options,
    validate_cose,
    verify_assertion,
    verify_registration,
)

GOLDEN = (
    Path(__file__).resolve().parents[2]
    / "qa"
    / "PHASE_02_CP3_C2_B2_C_RUNTIME_CANONICALIZATION_GAP_CODEX_REPORT.md"
)
FIELDS = {
    1: c.PRINCIPAL_FIELDS,
    4: c.CREDENTIAL_FIELDS,
    5: c.CREDENTIAL_FIELDS,
    7: c.CHALLENGE_FIELDS,
    8: c.AUTHENTICATION_FIELDS,
    9: c.ISSUER_CHALLENGE_FIELDS,
    10: c.ISSUER_AUTHENTICATION_FIELDS,
}


@pytest.mark.parametrize("number", range(1, 11))
def test_accepted_golden_vectors_byte_exact(number: int) -> None:
    document = GOLDEN.read_text(encoding="utf-8")
    section = document.split(f"### GV-{number:02d} —", 1)[1].split("### GV-", 1)[0]
    if number in (2, 3):
        raw = bytes.fromhex(section.split("CTAP2 canonical CBOR hex:\n")[1].splitlines()[0])
        assert validate_cose(raw)[0] == ("ES256" if number == 2 else "RS256")
        expected_text = section.split("expected cose_public_key_canonical:\n")[1].splitlines()[0]
        assert c.base64url(raw) == expected_text
        assert c.decode_base64url(expected_text) == raw
        assert (
            c.digest(raw) == section.split("expected public_key_fingerprint:\n")[1].splitlines()[0]
        )
    else:
        if "raw challenge hex:" in section:
            raw = bytes.fromhex(section.split("raw challenge hex:\n")[1].splitlines()[0])
            assert len(raw) == 32
            assert c.digest(raw) == section.split("expected challenge_digest:\n")[1].splitlines()[0]
        if number != 6:
            match = re.search(
                r"serialized UTF-8[^\n]*:\n(.*?)\nexpected [^\n]*:\n(sha256:[0-9a-f]{64})",
                section,
                re.DOTALL,
            )
            assert match is not None
            raw = "".join(match.group(1).splitlines()).encode("utf-8")
            payload = c.strict_json(raw)
            assert set(payload) == set(FIELDS[number])
            assert c.canonical_json(payload) == raw
            assert c.row_hash(payload, FIELDS[number]) == match.group(2)


def test_nfc_null_sort_order_integer_and_utc() -> None:
    assert (
        c.canonical_json({"z": None, "e\u0301": ["e\u0301", True, False, -123]})
        == '{"z":null,"é":["é",true,false,-123]}'.encode()
    )
    assert (
        c.canonical_json({"\U00010000": 1, "\ue000": 2}) == '{"\ue000":2,"\U00010000":1}'.encode()
    )
    assert c.utc_text(datetime(2026, 9, 5, tzinfo=UTC)) == "2026-09-05T00:00:00Z"
    assert (
        c.utc_text(datetime(2026, 9, 5, microsecond=1, tzinfo=UTC)) == "2026-09-05T00:00:00.000001Z"
    )
    with pytest.raises(c.ReviewerError):
        c.parse_utc("2026-09-05T00:00:00.1Z")


@pytest.mark.parametrize(
    "value", [float("nan"), float("inf"), 0.0, {"é": 1, "e\u0301": 2}, {1: 2}, "\ud800"]
)
def test_invalid_canonical_inputs(value: Any) -> None:
    with pytest.raises(c.ReviewerError):
        c.canonical_json(value)


@pytest.mark.parametrize("raw", ['{"x":1,"x":2}', '{"é":1,"e\\u0301":2}', "NaN", "1.0"])
def test_strict_json_rejects_ambiguous_bytes(raw: str) -> None:
    with pytest.raises(c.ReviewerError):
        c.strict_json(raw)


@pytest.mark.parametrize("value", ["", "Zg==", "Zh", "AA+", "AA/", "AA\n", 0, None])
def test_noncanonical_base64(value: Any) -> None:
    with pytest.raises(c.ReviewerError):
        c.decode_base64url(value)


def test_handle_and_option_contract() -> None:
    import hashlib

    expected = hashlib.sha256(
        b"issuer-steward-webauthn-user-handle/0.1.0\0principal\0operation"
    ).digest()
    assert c.user_handle("principal", "operation") == expected and len(expected) == 32
    options = registration_options(bytes(32), "principal", "operation")
    assert options["authenticatorSelection"] == {
        "authenticatorAttachment": "platform",
        "residentKey": "required",
        "requireResidentKey": True,
        "userVerification": "required",
    }
    assert options["attestation"] == "none" and options["extensions"] == {"credProps": True}
    assert options["user"]["id"] == c.base64url(expected)
    with pytest.raises(c.ReviewerError):
        assertion_options(bytes(32), (), 300000)


@pytest.mark.parametrize("remaining", [300, 600, 299, 1, 0, -1])
def test_child_expiry_exception_only(remaining: int) -> None:
    issued = datetime(2026, 9, 5, tzinfo=UTC)
    assert c.challenge_expiry(issued) == issued + timedelta(minutes=5)
    parent = issued + timedelta(seconds=remaining)
    if remaining <= 0:
        with pytest.raises(c.ReviewerError, match="EXPIRED"):
            c.challenge_expiry(issued, parent_expiry=parent)
    else:
        expiry = c.challenge_expiry(issued, parent_expiry=parent)
        assert timedelta(0) < expiry - issued <= timedelta(minutes=5)
        assert expiry <= parent
        assert expiry == min(issued + timedelta(minutes=5), parent)


@pytest.mark.parametrize("algorithm", ["ES256", "RS256"])
@pytest.mark.parametrize("invalid", [False, True])
def test_actual_signature_proofs(algorithm: str, invalid: bool) -> None:
    authenticator = Authenticator(algorithm)
    raw = secrets.token_bytes(32)
    creation = registration_options(raw, "principal", "registering-operation")
    registration = verify_registration(authenticator.registration(creation), c.digest(raw))
    assert registration.terminal_result == "SUCCEEDED"
    options = assertion_options(raw, (authenticator.identity,), 300000)
    facts = verify_assertion(
        authenticator.assertion(options, invalid=invalid),
        c.digest(raw),
        {authenticator.identity: (authenticator.cose, c.decode_base64url(authenticator.handle), 7)},
    )
    assert facts.terminal_result == ("INVALID_SIGNATURE" if invalid else "SUCCEEDED")
    assert facts.flags["signature_verified"] == int(not invalid)


@pytest.mark.parametrize(
    "changes",
    [
        {"origin": "http://127.0.0.1:3000"},
        {"origin": "http://localhost:3001"},
        {"origin": "https://localhost:3000"},
        {"origin": None},
        {"crossOrigin": True},
        {"crossOrigin": None},
        {"topOrigin": "http://localhost:3000"},
        {"challenge": c.base64url(bytes(32))},
        {"type": "webauthn.create"},
    ],
)
def test_assertion_exact_client_binding(changes: dict[str, Any]) -> None:
    authenticator = Authenticator()
    raw = secrets.token_bytes(32)
    options = assertion_options(raw, (authenticator.identity,), 300000)
    response = authenticator.assertion(options, **changes)
    facts = verify_assertion(
        response, c.digest(raw), {authenticator.identity: (authenticator.cose, bytes(32), 7)}
    )
    assert facts.terminal_result != "SUCCEEDED" and facts.flags["signature_verified"] == 0


@pytest.mark.parametrize("flags", [0, 1, 4])
def test_assertion_up_uv_required(flags: int) -> None:
    authenticator = Authenticator()
    raw = secrets.token_bytes(32)
    options = assertion_options(raw, (authenticator.identity,), 300000)
    facts = verify_assertion(
        authenticator.assertion(options, flags=flags),
        c.digest(raw),
        {authenticator.identity: (authenticator.cose, bytes(32), 7)},
    )
    assert facts.terminal_result in {"USER_PRESENCE_ABSENT", "USER_VERIFICATION_ABSENT"}


@pytest.mark.parametrize("handle", [None, c.base64url(bytes(32)), c.base64url(bytes([1]) * 32)])
def test_user_handle_present_absent_mismatch(handle: str | None) -> None:
    authenticator = Authenticator(handle=handle)
    raw = secrets.token_bytes(32)
    options = assertion_options(raw, (authenticator.identity,), 300000)
    facts = verify_assertion(
        authenticator.assertion(options),
        c.digest(raw),
        {authenticator.identity: (authenticator.cose, bytes(32), 7)},
    )
    assert facts.terminal_result == (
        "BINDING_MISMATCH" if handle == c.base64url(bytes([1]) * 32) else "SUCCEEDED"
    )
    if facts.terminal_result == "BINDING_MISMATCH":
        assert facts.safe_code == "USER_HANDLE_MISMATCH"


@pytest.mark.parametrize(
    "case",
    [
        "extra",
        "algorithm",
        "curve",
        "short_x",
        "bad_point",
        "noncanonical",
        "duplicate",
        "indefinite",
        "tag",
        "float",
        "trailing",
    ],
)
def test_restricted_es256_cbor_negatives(case: str) -> None:
    original = Authenticator().cose
    value = cbor2.loads(original)
    if case == "extra":
        value[4] = 1
    if case == "algorithm":
        value[3] = -8
    if case == "curve":
        value[-1] = 2
    if case == "short_x":
        value[-2] = bytes(31)
    if case == "bad_point":
        value[-2] = value[-3] = bytes(32)
    if case == "float":
        value[1] = 2.0
        float_algorithm = cbor2.loads(original)
        float_algorithm[3] = -7.0
        with pytest.raises(c.ReviewerError):
            validate_cose(cbor2.dumps(float_algorithm, canonical=True))
    raw = cbor2.dumps(value, canonical=True)
    if case == "noncanonical":
        raw = original.replace(b"\x01\x02", b"\x18\x01\x02", 1)
    if case == "duplicate":
        raw = b"\xa6" + original[1:] + b"\x01\x02"
    if case == "indefinite":
        raw = b"\xbf" + original[1:] + b"\xff"
    if case == "tag":
        raw = b"\xd8\x18" + original
    if case == "trailing":
        raw = original + b"\x00"
    with pytest.raises(c.ReviewerError):
        validate_cose(raw)


@pytest.mark.parametrize(
    "case", ["weak", "even", "leading_zero", "even_e", "small_e", "large_e", "extra"]
)
def test_restricted_rs256_negatives(case: str) -> None:
    value = cbor2.loads(Authenticator("RS256").cose)
    if case == "weak":
        value[-1] = b"\x7f" * 128
    if case == "even":
        value[-1] = value[-1][:-1] + b"\x02"
    if case == "leading_zero":
        value[-1] = b"\0" + value[-1]
    if case == "even_e":
        value[-2] = b"\x04"
    if case == "small_e":
        value[-2] = b"\x01"
    if case == "large_e":
        value[-2] = value[-1]
    if case == "extra":
        value[-3] = b"\x01"
    with pytest.raises(c.ReviewerError):
        validate_cose(cbor2.dumps(value, canonical=True))


@pytest.mark.parametrize(
    "case",
    [
        "attachment",
        "credprops_false",
        "credprops_absent",
        "up",
        "uv",
        "cose",
        "rp_hash",
        "authority_fields",
        "id_mismatch",
    ],
)
def test_registration_boundary_from_actual_authenticator_bytes(case: str) -> None:
    authenticator = Authenticator()
    raw = secrets.token_bytes(32)
    options = registration_options(raw, "principal", "operation")
    response = authenticator.registration(options)
    if case == "attachment":
        response["authenticatorAttachment"] = "cross-platform"
    if case == "credprops_false":
        response["clientExtensionResults"] = {"credProps": {"rk": False}}
    if case == "credprops_absent":
        del response["clientExtensionResults"]
    if case == "authority_fields":
        response["signature_verified"] = True
    if case == "id_mismatch":
        response["rawId"] = c.base64url(bytes(32))
    if case in ("up", "uv", "cose", "rp_hash"):
        object_value = cbor2.loads(c.decode_base64url(response["response"]["attestationObject"]))
        auth = bytearray(object_value["authData"])
        if case == "up":
            auth[32] &= ~1
        if case == "uv":
            auth[32] &= ~4
        if case == "rp_hash":
            auth[0] ^= 1
        if case == "cose":
            auth[-1] ^= 1
        object_value["authData"] = bytes(auth)
        response["response"]["attestationObject"] = c.base64url(cbor2.dumps(object_value))
    facts = verify_registration(response, c.digest(raw))
    assert (facts.terminal_result == "SUCCEEDED") is (case == "credprops_absent")
    if case != "credprops_absent":
        assert facts.material is None
