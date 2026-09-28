"""Unrouted R1 backend. Caller intent never supplies ledger authority fields."""

from __future__ import annotations

import secrets
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import Connection, Engine, create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError

from toss_dashboard_api.config import Settings

from . import canonical as c
from . import schema as s
from .ledger import Ledger, Row, insert, present, require, state_preimage
from .webauthn_core import (
    PublicMaterial,
    VerificationFacts,
    assertion_options,
    registration_options,
    verify_assertion,
    verify_registration,
)
from .windows_owner import canonical_database, verify_production_owner


def _id() -> str:
    return secrets.token_hex(32)


@dataclass(frozen=True)
class _ClockSample:
    """R1-generated times only; never apply to ledger reads or exact copies."""

    raw: datetime
    stored: datetime

    @classmethod
    def take(cls, clock: Callable[[], datetime]) -> _ClockSample:
        raw = clock()
        c.utc_text(raw)  # Validate UTC without changing canonical serialization.
        return cls(raw, raw.replace(microsecond=(raw.microsecond // 1000) * 1000))

    def check_sql(self, connection: Connection, *challenges: Row) -> None:
        """Detect, never repair, historical raw-time/frozen-SQL disagreement."""
        for challenge in challenges:
            if self.raw < c.parse_utc(challenge["issued_at"]):
                raise c.ReviewerError("SERVER_CLOCK_REGRESSION")
            sql_issued, sql_expired = connection.exec_driver_sql(
                "SELECT julianday(?) >= julianday(?), julianday(?) >= julianday(?)",
                (
                    c.utc_text(self.stored),
                    challenge["issued_at"],
                    c.utc_text(self.stored),
                    challenge["expires_at"],
                ),
            ).one()
            raw_expired = self.raw >= c.parse_utc(challenge["expires_at"])
            if sql_issued != 1 or sql_expired != int(raw_expired):
                raise c.ReviewerError("TIMESTAMP_PRECISION_CONFLICT")


def _require_time_profile(ledger: Ledger) -> None:
    """Immutable execution admission, not a historical-ledger normalization rule."""
    operation = ledger.operation_leaf
    if operation is None or ledger.find(
        s.OUTCOME, reviewer_credential_operation_id=operation[s.OPERATION.key]
    ):
        return
    for table, fields in (
        (s.CHALLENGE, ("issued_at", "expires_at")),
        (s.CONSUMPTION, ("consumed_at",)),
        (s.PENDING, ("verified_at",)),
        (s.CHILD, ("issued_at", "expires_at")),
    ):
        for row in ledger.find(table, reviewer_credential_operation_id=operation[s.OPERATION.key]):
            for field in fields:
                if c.parse_utc(row[field]).microsecond % 1000 != 0:
                    raise c.ReviewerError("R1_TIME_PROFILE_INCOMPATIBLE")


def _row(table: s.Table, now: datetime, *sources: Row, **overrides: Any) -> Row:
    merged: Row = {}
    for source in sources:
        merged.update(source)
    merged.update(overrides)
    fields = set(table.fields) | {table.key}
    if table is s.CREDENTIAL:
        fields.remove("authenticator_transports")
        fields.add("authenticator_transports_json")
    values = {field: merged.get(field) for field in fields}
    if values[table.key] is None:
        values[table.key] = _id()
    if table.time_column:
        values[table.time_column] = c.utc_text(now)
    return s.sealed(table, values)


@dataclass(frozen=True, repr=False)
class Ceremony:
    operation_id: str
    challenge_id: str
    purpose: str
    expires_at: str
    options: Row


@dataclass(frozen=True)
class Completed:
    operation_id: str
    outcome_id: str
    result: str


def _options(operation: Row, challenge: Row, raw: bytes, ledger: Ledger) -> Ceremony:
    purpose = challenge["challenge_purpose"]
    if purpose == "REGISTRATION_CREATE":
        options = registration_options(
            raw, operation["reviewer_principal_id"], operation["reviewer_credential_operation_id"]
        )
    else:
        allowed = (
            (challenge["webauthn_credential_id"],)
            if purpose == "COUNTER_CAPABILITY_ASSERTION"
            else tuple(sorted(ledger.active))
        )
        duration = c.parse_utc(challenge["expires_at"]) - c.parse_utc(challenge["issued_at"])
        timeout = max(1, duration // timedelta(milliseconds=1))
        options = assertion_options(raw, allowed, timeout)
    key = s.CHILD.key if purpose == "COUNTER_CAPABILITY_ASSERTION" else s.CHALLENGE.key
    return Ceremony(
        operation[s.OPERATION.key], challenge[key], purpose, challenge["expires_at"], options
    )


def _challenge(
    operation: Row, now: datetime, challenge_id: str, auth: Row | None = None
) -> tuple[Row, bytes]:
    raw = secrets.token_bytes(32)
    purpose = "REGISTRATION_CREATE" if auth is not None else operation["initial_challenge_purpose"]
    registration = purpose == "REGISTRATION_CREATE"
    row = _row(
        s.CHALLENGE,
        now,
        operation,
        reviewer_credential_operation_challenge_id=challenge_id,
        challenge_digest=c.digest(raw),
        challenge_nonce_length=32,
        challenge_purpose=purpose,
        rp_id=c.RP_ID,
        allowed_origin=c.ORIGIN,
        client_data_type="webauthn.create" if registration else "webauthn.get",
        user_verification_required=1,
        platform_attachment_required=1 if registration else None,
        resident_key_required=1 if registration else None,
        authentication_policy_version=c.POLICY,
        prerequisite_authentication_event_id=None if auth is None else auth[s.AUTHENTICATION.key],
        prerequisite_authentication_content_hash=None
        if auth is None
        else auth[s.AUTHENTICATION.hash_column],
        prerequisite_authentication_result=None if auth is None else "VERIFIED",
        issued_at=c.utc_text(now),
        expires_at=c.utc_text(c.challenge_expiry(now)),
    )
    return row, raw


def _material_values(material: PublicMaterial) -> Row:
    return {
        "webauthn_credential_id": material.credential_id,
        "credential_id_fingerprint": material.credential_fingerprint,
        "cose_public_key_canonical": c.base64url(material.cose),
        "public_key_fingerprint": material.key_fingerprint,
        "public_key_algorithm": material.algorithm,
        "authenticator_aaguid": material.aaguid,
        "authenticator_attachment": "platform",
        "authenticator_transports_json": c.canonical_json(list(material.transports)).decode(
            "utf-8"
        ),
        "rp_id": c.RP_ID,
        "resident_key_required": 1,
        "user_verification_required": 1,
        "registration_policy_version": c.POLICY,
    }


def _outcome_result(result: str) -> str:
    mapping = {
        "SUCCEEDED": "SUCCEEDED",
        "EXPIRED": "EXPIRED",
        "INVALID_SIGNATURE": "REJECTED",
        "USER_PRESENCE_ABSENT": "REJECTED",
        "USER_VERIFICATION_ABSENT": "REJECTED",
        "INVALID_REGISTRATION": "REJECTED",
        "BINDING_MISMATCH": "FAILED_CLOSED",
        "ORIGIN_RP_MISMATCH": "FAILED_CLOSED",
        "COUNTER_REJECTED": "FAILED_CLOSED",
        "REPLAY_REJECTED": "FAILED_CLOSED",
        "FAILED_CLOSED": "FAILED_CLOSED",
    }
    require(result in mapping)
    return mapping[result]


class _Runtime:
    """Lower-level transaction service, also used by isolated disposable-DB tests.

    The production factory below supplies a real owner check on every operation.
    This class is not exported through an HTTP endpoint or application container.
    """

    def __init__(
        self, engine: Engine, owner: Callable[[], str], clock: Callable[[], datetime] = c.server_now
    ) -> None:
        self._engine, self._owner, self._clock = engine, owner, clock

    @contextmanager
    def _transaction(self) -> Iterator[tuple[Connection, Ledger, str]]:
        owner = self._owner()
        try:
            with self._engine.connect() as connection:
                connection.exec_driver_sql("PRAGMA foreign_keys=ON")
                require(connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1)
                connection.commit()
                connection.exec_driver_sql("BEGIN IMMEDIATE")
                try:
                    ledger = Ledger(connection, owner)
                    _require_time_profile(ledger)
                    yield connection, ledger, owner
                    Ledger(connection, owner)
                    connection.commit()
                except BaseException:
                    connection.rollback()
                    raise
        except SQLAlchemyError:
            raise c.ReviewerError("REVIEWER_TRANSACTION_FAILED") from None

    def issue(
        self, operation_type: str, *, target_webauthn_credential_id: str | None = None
    ) -> Ceremony:
        if operation_type not in {
            "FIRST_ENROLLMENT",
            "ADD_CREDENTIAL",
            "REPLACE_CREDENTIAL",
            "REVOKE_CREDENTIAL",
        }:
            raise c.ReviewerError("INVALID_OPERATION_INTENT")
        targeting = operation_type in {"REPLACE_CREDENTIAL", "REVOKE_CREDENTIAL"}
        if targeting != (target_webauthn_credential_id is not None):
            raise c.ReviewerError("INVALID_TARGET_INTENT")
        if target_webauthn_credential_id is not None:
            c.decode_base64url(target_webauthn_credential_id)
        with self._transaction() as (connection, ledger, owner):
            predecessor = ledger.operation_leaf
            if predecessor is not None and not ledger.find(
                s.OUTCOME, reviewer_credential_operation_id=predecessor[s.OPERATION.key]
            ):
                raise c.ReviewerError("OPERATION_ALREADY_PENDING")
            if operation_type == "FIRST_ENROLLMENT":
                if ledger.rows(s.CREDENTIAL) or ledger.rows(s.EVENT):
                    raise c.ReviewerError("FIRST_ENROLLMENT_PERMANENTLY_CLOSED")
            elif not ledger.active:
                raise c.ReviewerError("NO_ACTIVE_AUTHORIZER")
            target = None
            if targeting:
                if target_webauthn_credential_id not in ledger.active:
                    raise c.ReviewerError("TARGET_NOT_ACTIVE")
                target = ledger.active[target_webauthn_credential_id][0]
            now = _ClockSample.take(self._clock).stored
            principal = ledger.principal
            if principal is None:
                require(operation_type == "FIRST_ENROLLMENT")
                principal = _row(
                    s.PRINCIPAL,
                    now,
                    reviewer_principal_id=_id(),
                    reviewer_role=c.ROLE,
                    principal_state="ACTIVE",
                    os_owner_sid_hash=owner,
                    enrollment_policy_version=c.POLICY,
                )
                insert(connection, s.PRINCIPAL, principal)
            expected = c.content_hash(state_preimage(principal, ledger.active))
            operation = _row(
                s.OPERATION,
                now,
                principal,
                reviewer_credential_operation_id=_id(),
                operation_type=operation_type,
                target_webauthn_credential_id=None
                if target is None
                else target["webauthn_credential_id"],
                target_credential_id_fingerprint=None
                if target is None
                else target["credential_id_fingerprint"],
                expected_credential_state_hash=expected,
                initial_challenge_id=_id(),
                initial_challenge_purpose="REGISTRATION_CREATE"
                if operation_type == "FIRST_ENROLLMENT"
                else "AUTHORIZATION_ASSERTION",
                predecessor_operation_id=None
                if predecessor is None
                else predecessor[s.OPERATION.key],
                operation_policy_version=c.POLICY,
            )
            challenge, raw = _challenge(operation, now, operation["initial_challenge_id"])
            insert(connection, s.OPERATION, operation)
            insert(connection, s.CHALLENGE, challenge)
            return _options(operation, challenge, raw, ledger)

    def complete(self, challenge_id: str, response: Any) -> Ceremony | Completed:
        error: str | None = None
        result: Ceremony | Completed
        if type(challenge_id) is not str:
            raise c.ReviewerError("UNKNOWN_CHALLENGE")
        with self._transaction() as (connection, ledger, owner):
            is_child = challenge_id in ledger.tables[s.CHILD.name]
            table = s.CHILD if is_child else s.CHALLENGE
            if type(challenge_id) is not str or challenge_id not in ledger.tables[table.name]:
                raise c.ReviewerError("UNKNOWN_CHALLENGE")
            challenge = ledger.get(table, challenge_id)
            operation = ledger.get(s.OPERATION, challenge[s.OPERATION.key])
            if ledger.find(s.OUTCOME, reviewer_credential_operation_id=operation[s.OPERATION.key]):
                raise c.ReviewerError("CHALLENGE_ALREADY_CONSUMED")
            if (
                is_child and ledger.find(s.BOOTSTRAP, counter_capability_challenge_id=challenge_id)
            ) or (
                not is_child
                and ledger.find(
                    s.CONSUMPTION, reviewer_credential_operation_challenge_id=challenge_id
                )
            ):
                raise c.ReviewerError("CHALLENGE_ALREADY_CONSUMED")
            pending = ledger.get(s.PENDING, challenge[s.PENDING.key]) if is_child else None
            if not is_child and ledger.find(s.PENDING, registration_challenge_id=challenge_id):
                raise c.ReviewerError("COUNTER_CONTINUATION_REQUIRED")
            parent = (
                ledger.get(s.CHALLENGE, challenge["parent_registration_challenge_id"])
                if is_child
                else challenge
            )
            now = self._clock()
            facts = VerificationFacts()
            try:
                ledger.bound_target(operation)
                if now < c.parse_utc(challenge["issued_at"]):
                    raise c.ReviewerError("SERVER_CLOCK_REGRESSION")
                if now >= c.parse_utc(challenge["expires_at"]) or now >= c.parse_utc(
                    parent["expires_at"]
                ):
                    facts = VerificationFacts(
                        terminal_result="EXPIRED", safe_code="CHALLENGE_EXPIRED"
                    )
                else:
                    # Snapshot caller bytes before verification; no caller trust fields.
                    wire = c.strict_json(c.canonical_json(response))
                    if is_child:
                        pending = present(pending)
                        allowed: dict[str, tuple[bytes, bytes, int | None]] = {
                            pending["webauthn_credential_id"]: (
                                c.decode_base64url(pending["cose_public_key_canonical"]),
                                c.user_handle(
                                    operation["reviewer_principal_id"], operation[s.OPERATION.key]
                                ),
                                0,
                            )
                        }
                        facts = verify_assertion(
                            wire, challenge["challenge_digest"], allowed, bootstrap=True
                        )
                    elif challenge["challenge_purpose"] == "REGISTRATION_CREATE":
                        facts = verify_registration(wire, challenge["challenge_digest"])
                    else:
                        facts = verify_assertion(
                            wire, challenge["challenge_digest"], ledger.allowed()
                        )
                facts.flags["replay_rejected"] = 1
                refreshed = Ledger(connection, owner)
                refreshed.bound_target(operation)
                ledger = refreshed
                if facts.material is not None and facts.terminal_result == "SUCCEEDED":
                    self._unique_material(ledger, facts.material)
            except c.LedgerCorruption:
                raise
            except c.ReviewerError as failure:
                facts.terminal_result, facts.safe_code = "FAILED_CLOSED", failure.code
            # Pre-projection revalidation is BEFORE the single decision/audit sample.
            # BEGIN IMMEDIATE excludes other writers throughout the following plan/inserts.
            ledger = Ledger(connection, self._owner())
            ledger.bound_target(operation)
            _require_time_profile(ledger)
            sample = _ClockSample.take(self._clock)
            if sample.raw < now:
                raise c.ReviewerError("SERVER_CLOCK_REGRESSION")
            sample.check_sql(connection, parent, challenge)
            if sample.raw >= c.parse_utc(challenge["expires_at"]) or sample.raw >= c.parse_utc(
                parent["expires_at"]
            ):
                facts.terminal_result, facts.safe_code = "EXPIRED", "CHALLENGE_EXPIRED"
            now = sample.stored
            if (
                facts.terminal_result == "SUCCEEDED"
                and facts.material is not None
                and facts.material.sign_count == 0
                and not is_child
            ):
                result = self._pending(connection, ledger, operation, challenge, facts, now)
            elif (
                facts.terminal_result == "SUCCEEDED"
                and challenge["challenge_purpose"] == "AUTHORIZATION_ASSERTION"
                and operation["operation_type"] in ("ADD_CREDENTIAL", "REPLACE_CREDENTIAL")
            ):
                result = self._authorized_continuation(
                    connection, ledger, operation, challenge, facts, now
                )
            else:
                result = self._terminal(
                    connection,
                    ledger,
                    operation,
                    parent,
                    facts,
                    now,
                    raw_now=sample.raw,
                    pending=pending,
                    child=challenge if is_child else None,
                )
                if facts.terminal_result != "SUCCEEDED":
                    error = facts.safe_code
        if error is not None:
            raise c.ReviewerError(error)
        return result

    @staticmethod
    def _unique_material(ledger: Ledger, material: PublicMaterial) -> None:
        if len(material.credential_id) > 512:
            raise c.ReviewerError("CREDENTIAL_ID_TOO_LONG")
        for row in ledger.rows(s.CREDENTIAL) + ledger.rows(s.PENDING):
            if (
                row["webauthn_credential_id"] == material.credential_id
                or row["credential_id_fingerprint"] == material.credential_fingerprint
                or row["public_key_fingerprint"] == material.key_fingerprint
            ):
                raise c.ReviewerError("CREDENTIAL_ALREADY_REGISTERED")

    def _pending(
        self,
        connection: Connection,
        ledger: Ledger,
        operation: Row,
        parent: Row,
        facts: VerificationFacts,
        now: datetime,
    ) -> Ceremony:
        _require_time_profile(ledger)
        public = present(facts.material)
        material = _material_values(public)
        child_id = _id()
        expiry = c.challenge_expiry(now, parent_expiry=c.parse_utc(parent["expires_at"]))
        representable = connection.exec_driver_sql(
            "SELECT julianday(?) > julianday(?) "
            "AND julianday(?) <= julianday(?, '+5 minutes') "
            "AND julianday(?) <= julianday(?)",
            (
                c.utc_text(expiry),
                c.utc_text(now),
                c.utc_text(expiry),
                c.utc_text(now),
                c.utc_text(expiry),
                parent["expires_at"],
            ),
        ).scalar_one()
        if representable != 1:
            raise c.ReviewerError("TIMESTAMP_PRECISION_CONFLICT")
        registration = _row(
            s.PENDING,
            now,
            operation,
            material,
            facts.flags,
            counter_capability_registration_id=_id(),
            registration_challenge_id=parent[s.CHALLENGE.key],
            registration_challenge_purpose="REGISTRATION_CREATE",
            registration_challenge_binding_hash=parent["challenge_binding_hash"],
            prerequisite_authentication_event_id=parent["prerequisite_authentication_event_id"],
            prerequisite_authentication_content_hash=parent[
                "prerequisite_authentication_content_hash"
            ],
            prerequisite_authentication_result=parent["prerequisite_authentication_result"],
            exact_origin=c.ORIGIN,
            require_resident_key=1,
            attestation_conveyance="none",
            cred_props_requested=1,
            cred_props_rk=public.cred_props_rk,
            observed_registration_sign_count=0,
            safe_result_code="COUNTER_CAPABILITY_CONTINUATION_REQUIRED",
            continuation_challenge_id=child_id,
        )
        raw = secrets.token_bytes(32)
        child = _row(
            s.CHILD,
            now,
            operation,
            registration,
            counter_capability_challenge_id=child_id,
            challenge_digest=c.digest(raw),
            challenge_nonce_length=32,
            challenge_purpose="COUNTER_CAPABILITY_ASSERTION",
            parent_registration_challenge_id=parent[s.CHALLENGE.key],
            parent_registration_challenge_binding_hash=parent["challenge_binding_hash"],
            allowed_origin=c.ORIGIN,
            client_data_type="webauthn.get",
            allow_credentials_count=1,
            allowed_webauthn_credential_id=material["webauthn_credential_id"],
            user_handle_contract_version=c.HANDLE_POLICY,
            authentication_policy_version=c.POLICY,
            issued_at=c.utc_text(now),
            expires_at=c.utc_text(expiry),
        )
        insert(connection, s.PENDING, registration)
        insert(connection, s.CHILD, child)
        return _options(operation, child, raw, ledger)

    @staticmethod
    def _consumption(
        operation: Row,
        challenge: Row,
        facts: VerificationFacts,
        now: datetime,
        resulting: str,
        *,
        outcome_id: str | None,
        continuation_id: str | None = None,
        credential: Row | None = None,
    ) -> Row:
        values = (
            {}
            if credential is None
            else {
                "registered_webauthn_credential_id": credential["webauthn_credential_id"],
                "registered_credential_content_hash": credential["credential_content_hash"],
                "registered_credential_id_fingerprint": credential["credential_id_fingerprint"],
                "registered_public_key_fingerprint": credential["public_key_fingerprint"],
                "registered_rp_id": credential["rp_id"],
                "registered_counter_capability": credential["counter_capability"],
                "registered_sign_count": credential["registration_sign_count"],
            }
        )
        return _row(
            s.CONSUMPTION,
            now,
            operation,
            challenge,
            facts.flags,
            values,
            challenge_consumption_id=_id(),
            terminal_result=facts.terminal_result,
            safe_result_code=facts.safe_code,
            terminal_operation_outcome_id=outcome_id,
            terminal_operation_outcome_result=None
            if outcome_id is None
            else _outcome_result(facts.terminal_result),
            outcome_expected_credential_state_hash=None
            if outcome_id is None
            else operation["expected_credential_state_hash"],
            outcome_resulting_credential_state_hash=None if outcome_id is None else resulting,
            continuation_challenge_id=continuation_id,
            continuation_challenge_purpose=None
            if continuation_id is None
            else "REGISTRATION_CREATE",
        )

    @staticmethod
    def _authentication(
        ledger: Ledger,
        operation: Row,
        challenge: Row,
        consumption: Row,
        facts: VerificationFacts,
        now: datetime,
    ) -> Row | None:
        if facts.credential_id not in ledger.active:
            return None
        credential = ledger.active[facts.credential_id][0]
        prior = ledger.counters[facts.credential_id]
        if prior is not None and facts.asserted_count is None:
            return None  # Not attributable without inventing a required counter value.
        return _row(
            s.AUTHENTICATION,
            now,
            operation,
            challenge,
            credential,
            facts.flags,
            credential_operation_authentication_event_id=_id(),
            challenge_consumption_id=consumption[s.CONSUMPTION.key],
            challenge_consumption_content_hash=consumption[s.CONSUMPTION.hash_column],
            challenge_terminal_result=facts.terminal_result,
            authorizing_webauthn_credential_id=facts.credential_id,
            authentication_result="VERIFIED"
            if facts.terminal_result == "SUCCEEDED"
            else "REJECTED",
            authentication_policy_version=c.POLICY,
            exact_origin=c.ORIGIN,
            previous_sign_count=prior,
            asserted_sign_count=None if prior is None else facts.asserted_count,
            safe_result_code=facts.safe_code,
        )

    def _authorized_continuation(
        self,
        connection: Connection,
        ledger: Ledger,
        operation: Row,
        challenge: Row,
        facts: VerificationFacts,
        now: datetime,
    ) -> Ceremony:
        _require_time_profile(ledger)
        continuation_id = _id()
        consumption = self._consumption(
            operation,
            challenge,
            facts,
            now,
            operation["expected_credential_state_hash"],
            outcome_id=None,
            continuation_id=continuation_id,
        )
        auth = self._authentication(ledger, operation, challenge, consumption, facts, now)
        auth = present(auth)
        continuation, raw = _challenge(operation, now, continuation_id, auth)
        insert(connection, s.CONSUMPTION, consumption)
        insert(connection, s.AUTHENTICATION, auth)
        insert(connection, s.CHALLENGE, continuation)
        return _options(operation, continuation, raw, ledger)

    def _terminal(
        self,
        connection: Connection,
        ledger: Ledger,
        operation: Row,
        parent: Row,
        facts: VerificationFacts,
        now: datetime,
        *,
        raw_now: datetime,
        pending: Row | None,
        child: Row | None,
    ) -> Completed:
        success = facts.terminal_result == "SUCCEEDED"
        child_facts = facts
        if pending is not None:
            overall = (
                "SUCCEEDED"
                if success
                else (
                    "EXPIRED" if raw_now >= c.parse_utc(parent["expires_at"]) else "FAILED_CLOSED"
                )
            )
            facts = VerificationFacts(
                terminal_result=overall,
                safe_code="COUNTER_CAPABILITY_SUPPORTED"
                if success and child_facts.asserted_count
                else (
                    "COUNTER_CAPABILITY_NO_USABLE_COUNTER"
                    if success
                    else "COUNTER_CAPABILITY_ASSERTION_FAILED"
                ),
            )
            facts.flags.update({key: pending[key] for key in facts.flags if key in pending})
        credential: Row | None = None
        events: list[tuple[Row, Row]] = []
        planned = dict(ledger.active)
        count: int | None
        if success and parent["challenge_purpose"] == "REGISTRATION_CREATE":
            if pending is None:
                public = present(facts.material)
                require(public.sign_count > 0)
                material = _material_values(public)
                capability, count = "SIGN_COUNT_SUPPORTED", public.sign_count
            else:
                material = pending
                capability = (
                    "SIGN_COUNT_SUPPORTED" if child_facts.asserted_count else "NO_USABLE_COUNTER"
                )
                count = 0 if capability == "SIGN_COUNT_SUPPORTED" else None
            credential = _row(
                s.CREDENTIAL,
                now,
                operation,
                material,
                counter_capability=capability,
                registration_sign_count=count,
            )
            event = _row(
                s.EVENT,
                now,
                credential,
                credential_event_id=_id(),
                event_type="REGISTERED",
                structured_reason_code="REGISTERED",
            )
            events.append((credential, event))
            planned[credential["webauthn_credential_id"]] = (credential, event)
        if success and operation["operation_type"] in ("REPLACE_CREDENTIAL", "REVOKE_CREDENTIAL"):
            target = present(ledger.bound_target(operation))
            root = ledger.active[target["webauthn_credential_id"]][1]
            event_type = (
                "SUPERSEDED" if operation["operation_type"] == "REPLACE_CREDENTIAL" else "REVOKED"
            )
            event = _row(
                s.EVENT,
                now,
                target,
                credential_event_id=_id(),
                event_type=event_type,
                structured_reason_code=event_type,
                supersedes_credential_event_id=root[s.EVENT.key],
            )
            events.append((target, event))
            del planned[target["webauthn_credential_id"]]
        principal = present(ledger.principal)
        resulting = (
            c.content_hash(state_preimage(principal, planned))
            if success
            else operation["expected_credential_state_hash"]
        )
        outcome_id = _id()
        consumption = self._consumption(
            operation, parent, facts, now, resulting, outcome_id=outcome_id, credential=credential
        )
        auth = None
        if parent["prerequisite_authentication_event_id"] is not None:
            auth = ledger.get(s.AUTHENTICATION, parent["prerequisite_authentication_event_id"])
        elif parent["challenge_purpose"] == "AUTHORIZATION_ASSERTION":
            auth = self._authentication(ledger, operation, parent, consumption, facts, now)
        registration = consumption if parent["challenge_purpose"] == "REGISTRATION_CREATE" else None
        outcome = _row(
            s.OUTCOME,
            now,
            operation,
            credential_operation_outcome_id=outcome_id,
            terminal_result=_outcome_result(facts.terminal_result),
            terminal_consumption_id=consumption[s.CONSUMPTION.key],
            terminal_consumption_content_hash=consumption[s.CONSUMPTION.hash_column],
            terminal_challenge_purpose=parent["challenge_purpose"],
            terminal_challenge_result=facts.terminal_result,
            authorization_authentication_event_id=None
            if auth is None
            else auth[s.AUTHENTICATION.key],
            authorization_authentication_content_hash=None
            if auth is None
            else auth[s.AUTHENTICATION.hash_column],
            authorization_authentication_result=None
            if auth is None
            else auth["authentication_result"],
            registration_consumption_id=None
            if registration is None
            else registration[s.CONSUMPTION.key],
            registration_consumption_content_hash=None
            if registration is None
            else registration[s.CONSUMPTION.hash_column],
            registration_challenge_purpose=None if registration is None else "REGISTRATION_CREATE",
            registration_terminal_result=None if registration is None else facts.terminal_result,
            resulting_credential_state_hash=resulting,
            safe_result_code=facts.safe_code,
        )
        authorizations = [
            self._authorization(operation, item, event, outcome, registration, auth, now)
            for item, event in events
        ]
        if pending is not None:
            child = present(child)
            bootstrap = self._bootstrap(
                operation,
                pending,
                child,
                child_facts,
                consumption,
                outcome,
                credential,
                events,
                authorizations,
                now,
            )
            insert(connection, s.BOOTSTRAP, bootstrap)
        insert(connection, s.CONSUMPTION, consumption)
        if auth is not None and parent["challenge_purpose"] == "AUTHORIZATION_ASSERTION":
            insert(connection, s.AUTHENTICATION, auth)
        for authorization in authorizations:
            insert(connection, s.AUTHORIZATION, authorization)
        if credential is not None:
            insert(connection, s.CREDENTIAL, credential)
        for _item, event in events:
            insert(connection, s.EVENT, event)
        # Independently load every credential/event before the deferred outcome.
        # Require exact identity and content equality with the projected graph.
        current_credentials = {
            row["webauthn_credential_id"]: dict(row)
            for row in connection.exec_driver_sql(f"SELECT * FROM {s.CREDENTIAL.name}").mappings()
        }
        current_events = {
            row[s.EVENT.key]: dict(row)
            for row in connection.exec_driver_sql(f"SELECT * FROM {s.EVENT.name}").mappings()
        }
        expected_credentials = {**ledger.tables[s.CREDENTIAL.name]}
        if credential:
            expected_credentials[credential["webauthn_credential_id"]] = credential
        expected_events = {
            **ledger.tables[s.EVENT.name],
            **{event[s.EVENT.key]: event for _item, event in events},
        }
        require(current_credentials == expected_credentials and current_events == expected_events)
        reloaded_active: dict[str, tuple[Row, Row]] = {}
        for identity, item in current_credentials.items():
            chain = [
                event
                for event in current_events.values()
                if event["webauthn_credential_id"] == identity
            ]
            require(len(chain) in (1, 2))
            if len(chain) == 1:
                require(
                    chain[0]["event_type"] == "REGISTERED"
                    and chain[0]["supersedes_credential_event_id"] is None
                )
                reloaded_active[identity] = (item, chain[0])
        require(c.content_hash(state_preimage(principal, reloaded_active)) == resulting)
        insert(connection, s.OUTCOME, outcome)
        return Completed(operation[s.OPERATION.key], outcome_id, outcome["terminal_result"])

    @staticmethod
    def _authorization(
        operation: Row,
        credential: Row,
        event: Row,
        outcome: Row,
        registration: Row | None,
        auth: Row | None,
        now: datetime,
    ) -> Row:
        registered = event["event_type"] == "REGISTERED"
        kind = (
            "BOOTSTRAP_REGISTRATION"
            if operation["operation_type"] == "FIRST_ENROLLMENT"
            else (
                "AUTHORIZED_REGISTRATION"
                if registered
                else (
                    "AUTHORIZED_SUPERSESSION"
                    if event["event_type"] == "SUPERSEDED"
                    else "AUTHORIZED_REVOCATION"
                )
            )
        )
        registration = registration if registered else None
        return _row(
            s.AUTHORIZATION,
            now,
            operation,
            credential,
            event,
            webauthn_credential_content_hash=credential["credential_content_hash"],
            authorization_kind=kind,
            registration_consumption_id=None
            if registration is None
            else registration[s.CONSUMPTION.key],
            registration_consumption_content_hash=None
            if registration is None
            else registration[s.CONSUMPTION.hash_column],
            registration_challenge_purpose=None if registration is None else "REGISTRATION_CREATE",
            registration_terminal_result=None if registration is None else "SUCCEEDED",
            credential_operation_authentication_event_id=None
            if auth is None
            else auth[s.AUTHENTICATION.key],
            credential_operation_authentication_content_hash=None
            if auth is None
            else auth[s.AUTHENTICATION.hash_column],
            credential_operation_authentication_result=None
            if auth is None
            else auth["authentication_result"],
            credential_operation_outcome_id=outcome[s.OUTCOME.key],
            credential_operation_outcome_content_hash=outcome[s.OUTCOME.hash_column],
            credential_operation_outcome_result="SUCCEEDED",
            resulting_credential_state_hash=outcome["resulting_credential_state_hash"],
        )

    @staticmethod
    def _bootstrap(
        operation: Row,
        pending: Row,
        child: Row,
        facts: VerificationFacts,
        consumption: Row,
        outcome: Row,
        credential: Row | None,
        events: list[tuple[Row, Row]],
        authorizations: list[Row],
        now: datetime,
    ) -> Row:
        success = facts.terminal_result == "SUCCEEDED"
        values: Row = {}
        for kind, index in (("registered", 0), ("superseded", 1)):
            if index < len(events):
                values.update(
                    {
                        f"projected_{kind}_event_id": events[index][1][s.EVENT.key],
                        f"projected_{kind}_event_content_hash": events[index][1][
                            s.EVENT.hash_column
                        ],
                        f"projected_{kind}_authorization_content_hash": authorizations[index][
                            s.AUTHORIZATION.hash_column
                        ],
                    }
                )
        return _row(
            s.BOOTSTRAP,
            now,
            operation,
            pending,
            child,
            facts.flags,
            values,
            counter_capability_assertion_id=_id(),
            challenge_terminal_result=facts.terminal_result,
            safe_result_code=facts.safe_code,
            user_handle_status=facts.user_handle_status,
            previous_sign_count=0 if facts.flags["signature_verified"] else None,
            asserted_sign_count=facts.asserted_count if facts.flags["signature_verified"] else None,
            selected_counter_capability=None
            if credential is None
            else credential["counter_capability"],
            selected_registration_sign_count=None
            if credential is None
            else credential["registration_sign_count"],
            classification_verified=int(success),
            projected_registration_consumption_id=consumption[s.CONSUMPTION.key],
            projected_registration_consumption_content_hash=consumption[s.CONSUMPTION.hash_column],
            projected_registration_challenge_purpose="REGISTRATION_CREATE",
            projected_registration_terminal_result=consumption["terminal_result"],
            projected_registration_safe_result_code=consumption["safe_result_code"],
            projected_operation_outcome_id=outcome[s.OUTCOME.key],
            projected_operation_outcome_content_hash=outcome[s.OUTCOME.hash_column],
            projected_operation_terminal_result=outcome["terminal_result"],
            projected_resulting_credential_state_hash=outcome["resulting_credential_state_hash"],
            projected_credential_content_hash=None
            if credential is None
            else credential["credential_content_hash"],
        )


def create_reviewer_service() -> _Runtime:
    """Production-only factory. No caller SID/path/policy or bypass options."""
    settings = Settings()
    url = make_url(settings.database_url)
    expected = canonical_database()
    database = url.database
    if url.drivername not in ("sqlite", "sqlite+pysqlite") or url.query or not database:
        raise c.ReviewerError("NONCANONICAL_AUTHORITY_DATABASE")
    path = (
        expected
        if database.replace("\\", "/") in ("./var/dashboard.db", "var/dashboard.db")
        else Path(database)
    )
    verify_production_owner(path)
    engine = create_engine("sqlite+pysqlite:///" + expected.as_posix(), hide_parameters=True)
    return _Runtime(engine, lambda: verify_production_owner(expected))
