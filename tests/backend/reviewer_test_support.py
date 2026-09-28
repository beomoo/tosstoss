"""Ephemeral synthetic authenticators: real signatures, no stored private keys."""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import cbor2
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa

from toss_dashboard_api.reviewer.canonical import ORIGIN, RP_ID, base64url, canonical_json


@dataclass
class Clock:
    value: datetime = datetime(2026, 9, 5, 0, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.value


@dataclass(repr=False)
class Authenticator:
    algorithm: str = "ES256"
    credential_id: bytes = field(default_factory=lambda: secrets.token_bytes(32))
    key: Any = field(init=False)
    cose: bytes = field(init=False)
    handle: str | None = None

    def __post_init__(self) -> None:
        if self.algorithm == "ES256":
            self.key = ec.generate_private_key(ec.SECP256R1())
            numbers = self.key.public_key().public_numbers()
            value = {
                1: 2,
                3: -7,
                -1: 1,
                -2: numbers.x.to_bytes(32, "big"),
                -3: numbers.y.to_bytes(32, "big"),
            }
        else:
            self.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            numbers = self.key.public_key().public_numbers()
            value = {
                1: 3,
                3: -257,
                -1: numbers.n.to_bytes(256, "big"),
                -2: numbers.e.to_bytes(3, "big"),
            }
        self.cose = cbor2.dumps(value, canonical=True)

    @property
    def identity(self) -> str:
        return base64url(self.credential_id)

    def client(self, issued_challenge: str, expected_kind: str, **values: Any) -> bytes:
        return canonical_json(
            {
                "type": expected_kind,
                "challenge": issued_challenge,
                "origin": ORIGIN,
                "crossOrigin": False,
                **values,
            }
        )

    def registration(
        self, options: dict[str, Any], count: int = 7, *, flags: int = 0x45, **client_values: Any
    ) -> dict[str, Any]:
        self.handle = options["user"]["id"]
        client = self.client(options["challenge"], "webauthn.create", **client_values)
        auth_data = (
            hashlib.sha256(RP_ID.encode("ascii")).digest()
            + bytes([flags])
            + count.to_bytes(4, "big")
            + bytes(16)
            + len(self.credential_id).to_bytes(2, "big")
            + self.credential_id
            + self.cose
        )
        return {
            "id": self.identity,
            "rawId": self.identity,
            "type": "public-key",
            "authenticatorAttachment": "platform",
            "clientExtensionResults": {"credProps": {"rk": True}},
            "response": {
                "clientDataJSON": base64url(client),
                "attestationObject": base64url(
                    cbor2.dumps({"fmt": "none", "authData": auth_data, "attStmt": {}})
                ),
                "transports": ["internal"],
            },
        }

    def assertion(
        self,
        options: dict[str, Any],
        count: int = 8,
        *,
        flags: int = 5,
        invalid: bool = False,
        **client_values: Any,
    ) -> dict[str, Any]:
        client = self.client(options["challenge"], "webauthn.get", **client_values)
        auth_data = (
            hashlib.sha256(RP_ID.encode("ascii")).digest()
            + bytes([flags])
            + count.to_bytes(4, "big")
        )
        message = auth_data + hashlib.sha256(client).digest()
        signature = (
            self.key.sign(message, ec.ECDSA(hashes.SHA256()))
            if self.algorithm == "ES256"
            else self.key.sign(message, padding.PKCS1v15(), hashes.SHA256())
        )
        if invalid:
            signature = signature[:-1] + bytes([signature[-1] ^ 1])
        return {
            "id": self.identity,
            "rawId": self.identity,
            "type": "public-key",
            "authenticatorAttachment": "platform",
            "response": {
                "clientDataJSON": base64url(client),
                "authenticatorData": base64url(auth_data),
                "signature": base64url(signature),
                "userHandle": self.handle,
            },
        }
