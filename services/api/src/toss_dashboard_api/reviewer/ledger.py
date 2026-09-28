"""Read and reconstruct immutable reviewer graphs inside a writer transaction."""

from __future__ import annotations

from typing import Any

from sqlalchemy import Connection

from . import canonical as c
from . import schema as s
from .webauthn_core import validate_cose

Row = dict[str, Any]


def present[T](value: T | None) -> T:
    if value is None:
        raise c.LedgerCorruption()
    return value


def require(condition: bool) -> None:
    if not condition:
        raise c.LedgerCorruption()


def copy_fields(row: Row, fields: list[str]) -> Row:
    return {name: row[name] for name in fields}


def insert(connection: Connection, table: s.Table, row: Row) -> None:
    require(table in s.WRITE_TABLES)
    allowed = set(table.fields) | {table.key, table.hash_column, "payload_json"}
    if table.time_column:
        allowed.add(table.time_column)
    if table is s.CREDENTIAL:
        allowed.remove("authenticator_transports")
        allowed.add("authenticator_transports_json")
    require(set(row) == allowed and row[table.hash_column] == table.hash(row))
    # Identifiers come exclusively from the explicit server inventory above.
    columns = sorted(allowed)
    connection.exec_driver_sql(
        f"INSERT INTO {table.name} ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})",
        tuple(row[key] for key in columns),
    )


def state_preimage(principal: Row, active: dict[str, tuple[Row, Row]]) -> Row:
    members: list[Row] = []
    for credential, event in active.values():
        member = copy_fields(
            credential,
            """authenticator_attachment counter_capability
credential_id_fingerprint public_key_algorithm public_key_fingerprint registration_policy_version
rp_id webauthn_credential_id""".split(),
        )
        member.update(
            credential_contract_version=credential["contract_version"],
            resident_key_required=True,
            user_verification_required=True,
            lifecycle_leaf={
                "credential_event_content_hash": event["credential_event_content_hash"],
                "credential_event_contract_version": event["contract_version"],
                "credential_event_id": event["credential_event_id"],
                "event_type": event["event_type"],
            },
        )
        members.append(member)
    members.sort(
        key=lambda row: (
            row["credential_id_fingerprint"].encode("utf-8"),
            row["webauthn_credential_id"].encode("utf-8"),
            row["lifecycle_leaf"]["credential_event_id"].encode("utf-8"),
        )
    )
    return {
        **copy_fields(
            principal,
            "reviewer_principal_id reviewer_role principal_content_hash os_owner_sid_hash".split(),
        ),
        "contract_version": "reviewer-credential-state/0.1.0",
        "active_credentials": members,
    }


class Ledger:
    """A transaction snapshot. Malformed rows are never dropped or normalized away."""

    def __init__(self, connection: Connection, owner_hash: str) -> None:
        self.connection = connection
        self.tables: dict[str, dict[str, Row]] = {}
        # FK copies are structural evidence, not a replacement for content hashes.
        require(not connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall())
        for table in s.READ_TABLES:
            rows: dict[str, Row] = {}
            for mapping in connection.exec_driver_sql(f"SELECT * FROM {table.name}").mappings():
                row = dict(mapping)
                require(row[table.key] not in rows)
                require(row["contract_version"] == table.version)
                require(row[table.hash_column] == table.hash(row))
                if table.time_column:
                    c.parse_utc(row[table.time_column])
                for field in table.fields:
                    if field.endswith("policy_version"):
                        require(row[field] == c.POLICY)
                if "reviewer_role" in row:
                    require(row["reviewer_role"] == c.ROLE)
                rows[row[table.key]] = row
            self.tables[table.name] = rows
        principals = list(self.rows(s.PRINCIPAL))
        require(len(principals) <= 1)
        self.principal = principals[0] if principals else None
        self.active: dict[str, tuple[Row, Row]] = {}
        self.registration_operations: dict[str, str] = {}
        self.counters: dict[str, int | None] = {}
        self.operation_leaf: Row | None = None
        if self.principal is None:
            require(all(not rows for rows in self.tables.values()))
            self.state_hash: str | None = None
            return
        require(self.principal["principal_state"] == "ACTIVE")
        if self.principal["os_owner_sid_hash"] != owner_hash:
            raise c.ReviewerError("OWNER_PRINCIPAL_BINDING_MISMATCH")
        for rows in self.tables.values():
            for row in rows.values():
                require(row["reviewer_principal_id"] == self.principal["reviewer_principal_id"])
                if "principal_content_hash" in row:
                    require(
                        row["principal_content_hash"] == self.principal["principal_content_hash"]
                    )
                if "os_owner_sid_hash" in row:
                    require(row["os_owner_sid_hash"] == owner_hash)
        self._credentials()
        self.state_hash = c.content_hash(state_preimage(self.principal, self.active))
        self._operations()
        self._challenges()

    def rows(self, table: s.Table) -> list[Row]:
        return list(self.tables[table.name].values())

    def get(self, table: s.Table, identity: str) -> Row:
        try:
            return self.tables[table.name][identity]
        except KeyError:
            raise c.LedgerCorruption() from None

    def find(self, table: s.Table, **values: Any) -> list[Row]:
        return [
            row
            for row in self.rows(table)
            if all(row[key] == value for key, value in values.items())
        ]

    def _credentials(self) -> None:
        seen_ids: set[str] = set()
        seen_keys: set[str] = set()
        all_events: set[str] = set()
        for credential in self.rows(s.CREDENTIAL):
            identity = credential["webauthn_credential_id"]
            raw_id = c.decode_base64url(identity)
            require(
                len(identity) <= 512 and c.digest(raw_id) == credential["credential_id_fingerprint"]
            )
            cose = c.decode_base64url(credential["cose_public_key_canonical"])
            algorithm, _key = validate_cose(cose)
            require(
                algorithm == credential["public_key_algorithm"]
                and c.digest(cose) == credential["public_key_fingerprint"]
            )
            require(
                credential["credential_id_fingerprint"] not in seen_ids
                and credential["public_key_fingerprint"] not in seen_keys
            )
            seen_ids.add(credential["credential_id_fingerprint"])
            seen_keys.add(credential["public_key_fingerprint"])
            require(
                credential["authenticator_attachment"] == "platform"
                and credential["rp_id"] == c.RP_ID
            )
            require(
                credential["resident_key_required"] == credential["user_verification_required"] == 1
            )
            transports = c.strict_json(credential["authenticator_transports_json"])
            require(type(transports) is list and all(type(item) is str for item in transports))
            require(
                transports == sorted(set(transports))
                and set(transports) <= {"ble", "hybrid", "internal", "nfc", "smart-card", "usb"}
            )
            events = self.find(s.EVENT, webauthn_credential_id=identity)
            roots = [row for row in events if row["supersedes_credential_event_id"] is None]
            require(
                len(roots) == 1 and roots[0]["event_type"] == "REGISTERED" and len(events) in (1, 2)
            )
            root = roots[0]
            for event in events:
                require(event["credential_event_id"] not in all_events)
                all_events.add(event["credential_event_id"])
                if event is not root:
                    require(
                        event["supersedes_credential_event_id"] == root["credential_event_id"]
                        and event["event_type"] in ("REVOKED", "SUPERSEDED")
                    )
                authorization = self.get(s.AUTHORIZATION, event["credential_event_id"])
                require(
                    authorization["credential_event_content_hash"]
                    == event["credential_event_content_hash"]
                )
                require(
                    authorization["webauthn_credential_content_hash"]
                    == credential["credential_content_hash"]
                    and authorization["event_type"] == event["event_type"]
                )
                outcome = self.get(s.OUTCOME, authorization["credential_operation_outcome_id"])
                require(
                    outcome["terminal_result"] == "SUCCEEDED"
                    and outcome["outcome_content_hash"]
                    == authorization["credential_operation_outcome_content_hash"]
                )
                for field in (
                    "reviewer_credential_operation_id",
                    "operation_content_hash",
                    "expected_credential_state_hash",
                    "resulting_credential_state_hash",
                ):
                    require(authorization[field] == outcome[field])
                operation = self.get(s.OPERATION, authorization["reviewer_credential_operation_id"])
                kinds = {
                    ("FIRST_ENROLLMENT", "REGISTERED"): "BOOTSTRAP_REGISTRATION",
                    ("ADD_CREDENTIAL", "REGISTERED"): "AUTHORIZED_REGISTRATION",
                    ("REPLACE_CREDENTIAL", "REGISTERED"): "AUTHORIZED_REGISTRATION",
                    ("REPLACE_CREDENTIAL", "SUPERSEDED"): "AUTHORIZED_SUPERSESSION",
                    ("REVOKE_CREDENTIAL", "REVOKED"): "AUTHORIZED_REVOCATION",
                }
                require(
                    kinds.get((operation["operation_type"], event["event_type"]))
                    == authorization["authorization_kind"]
                )
                if event is root:
                    self.registration_operations[identity] = operation[
                        "reviewer_credential_operation_id"
                    ]
                else:
                    require(
                        operation["target_webauthn_credential_id"] == identity
                        and operation["target_credential_id_fingerprint"]
                        == credential["credential_id_fingerprint"]
                    )
            if len(events) == 1:
                self.active[identity] = (credential, root)
            self.counters[identity] = self._counter(credential)
        require(
            all_events == set(self.tables[s.EVENT.name]) == set(self.tables[s.AUTHORIZATION.name])
        )
        for table, column in (
            (s.AUTHENTICATION, "authorizing_webauthn_credential_id"),
            (s.ISSUER_AUTHENTICATION, "webauthn_credential_id"),
        ):
            for row in self.rows(table):
                require(row[column] in self.tables[s.CREDENTIAL.name])

    def _counter(self, credential: Row) -> int | None:
        identity = credential["webauthn_credential_id"]
        capability = credential["counter_capability"]
        require(capability in ("SIGN_COUNT_SUPPORTED", "NO_USABLE_COUNTER"))
        edges: list[tuple[int, int]] = []
        ordinary = self.find(
            s.AUTHENTICATION, authorizing_webauthn_credential_id=identity
        ) + self.find(s.ISSUER_AUTHENTICATION, webauthn_credential_id=identity)
        for row in ordinary:
            require(row["counter_capability"] == capability)
            require(
                row["credential_id_fingerprint"] == credential["credential_id_fingerprint"]
                and row["public_key_fingerprint"] == credential["public_key_fingerprint"]
            )
            require(row["rp_id"] == c.RP_ID and row["exact_origin"] == c.ORIGIN)
            if capability == "NO_USABLE_COUNTER":
                require(row["previous_sign_count"] is None and row["asserted_sign_count"] is None)
            else:
                require(
                    type(row["previous_sign_count"]) is int
                    and type(row["asserted_sign_count"]) is int
                )
            require(row["authentication_result"] in ("VERIFIED", "REJECTED"))
            if row["authentication_result"] == "VERIFIED":
                require(
                    all(
                        row[name] == 1
                        for name in (
                            "user_presence_verified user_verification_verified origin_verified "
                            "rp_id_hash_verified signature_verified "
                            "counter_verified replay_rejected"
                        ).split()
                    )
                )
                if capability == "SIGN_COUNT_SUPPORTED":
                    edges.append((row["previous_sign_count"], row["asserted_sign_count"]))
        bootstrap = self.find(
            s.BOOTSTRAP, webauthn_credential_id=identity, challenge_terminal_result="SUCCEEDED"
        )
        require(len(bootstrap) <= 1)
        for row in bootstrap:
            require(
                row["projected_credential_content_hash"] == credential["credential_content_hash"]
                and row["selected_counter_capability"] == capability
            )
            require(
                row["previous_sign_count"] == 0
                and row["signature_verified"] == row["classification_verified"] == 1
            )
            if capability == "SIGN_COUNT_SUPPORTED":
                edges.append((0, row["asserted_sign_count"]))
            else:
                require(
                    row["asserted_sign_count"] == 0
                    and row["selected_registration_sign_count"] is None
                )
        prior = credential["registration_sign_count"]
        if capability == "NO_USABLE_COUNTER":
            require(prior is None and len(bootstrap) == 1)
            return None
        require(type(prior) is int and prior >= 0 and (prior != 0 or len(bootstrap) == 1))
        outgoing: dict[int, int] = {}
        incoming: set[int] = set()
        for previous, asserted in edges:
            require(
                type(previous) is int
                and type(asserted) is int
                and 0 <= previous < asserted <= 0xFFFFFFFF
            )
            require(previous not in outgoing and asserted not in incoming)
            outgoing[previous] = asserted
            incoming.add(asserted)
        visited = 0
        while prior in outgoing:
            prior = outgoing[prior]
            visited += 1
        require(visited == len(edges))
        return int(prior)

    def _operations(self) -> None:
        operations = self.rows(s.OPERATION)
        if not operations:
            require(not self.rows(s.CREDENTIAL))
            return
        roots = [row for row in operations if row["predecessor_operation_id"] is None]
        require(len(roots) == 1 and roots[0]["operation_type"] == "FIRST_ENROLLMENT")
        current = roots[0]
        previous_state = c.content_hash(state_preimage(present(self.principal), {}))
        visited: set[str] = set()
        while True:
            identity = current["reviewer_credential_operation_id"]
            require(
                identity not in visited
                and current["expected_credential_state_hash"] == previous_state
            )
            visited.add(identity)
            initial = self.get(s.CHALLENGE, current["initial_challenge_id"])
            require(
                initial["reviewer_credential_operation_id"] == identity
                and initial["challenge_purpose"] == current["initial_challenge_purpose"]
            )
            outcomes = self.find(s.OUTCOME, reviewer_credential_operation_id=identity)
            require(len(outcomes) <= 1)
            if outcomes:
                outcome = outcomes[0]
                consumption = self.get(s.CONSUMPTION, outcome["terminal_consumption_id"])
                require(
                    consumption["terminal_operation_outcome_id"]
                    == outcome["credential_operation_outcome_id"]
                    and consumption["consumption_content_hash"]
                    == outcome["terminal_consumption_content_hash"]
                )
                require(
                    outcome["expected_credential_state_hash"]
                    == current["expected_credential_state_hash"]
                    and outcome["operation_content_hash"] == current["operation_content_hash"]
                )
                if outcome["terminal_result"] != "SUCCEEDED":
                    require(outcome["resulting_credential_state_hash"] == previous_state)
                previous_state = outcome["resulting_credential_state_hash"]
            successors = [row for row in operations if row["predecessor_operation_id"] == identity]
            require(len(successors) <= 1 and (not successors or bool(outcomes)))
            if not successors:
                self.operation_leaf = current
                break
            current = successors[0]
        require(len(visited) == len(operations) and previous_state == self.state_hash)
        require(
            all(row["reviewer_credential_operation_id"] in visited for row in self.rows(s.OUTCOME))
        )

    def _challenges(self) -> None:
        for challenge in self.rows(s.CHALLENGE):
            operation = self.get(s.OPERATION, challenge["reviewer_credential_operation_id"])
            for field in (
                "operation_content_hash operation_type expected_credential_state_hash "
                "target_webauthn_credential_id target_credential_id_fingerprint"
            ).split():
                require(challenge[field] == operation[field])
            issued, expiry = (
                c.parse_utc(challenge["issued_at"]),
                c.parse_utc(challenge["expires_at"]),
            )
            require(expiry == c.challenge_expiry(issued))
            require(
                challenge["rp_id"] == c.RP_ID
                and challenge["allowed_origin"] == c.ORIGIN
                and challenge["challenge_nonce_length"] == 32
            )
            if challenge["prerequisite_authentication_event_id"]:
                auth = self.get(s.AUTHENTICATION, challenge["prerequisite_authentication_event_id"])
                require(
                    auth["authentication_result"] == "VERIFIED"
                    and auth["authentication_content_hash"]
                    == challenge["prerequisite_authentication_content_hash"]
                    and auth["reviewer_credential_operation_id"]
                    == operation["reviewer_credential_operation_id"]
                )
        for child in self.rows(s.CHILD):
            parent = self.get(s.CHALLENGE, child["parent_registration_challenge_id"])
            pending = self.get(s.PENDING, child["counter_capability_registration_id"])
            require(
                pending["continuation_challenge_id"] == child["counter_capability_challenge_id"]
            )
            require(
                child["parent_registration_challenge_binding_hash"]
                == parent["challenge_binding_hash"]
            )
            require(
                c.parse_utc(child["expires_at"])
                == c.challenge_expiry(
                    c.parse_utc(child["issued_at"]), parent_expiry=c.parse_utc(parent["expires_at"])
                )
            )
        for consumption in self.rows(s.CONSUMPTION):
            challenge = self.get(
                s.CHALLENGE, consumption["reviewer_credential_operation_challenge_id"]
            )
            require(consumption["challenge_binding_hash"] == challenge["challenge_binding_hash"])
            if consumption["terminal_operation_outcome_id"] is not None:
                outcome = self.get(s.OUTCOME, consumption["terminal_operation_outcome_id"])
                require(
                    outcome["terminal_consumption_id"] == consumption["challenge_consumption_id"]
                )
            else:
                continuation = self.get(s.CHALLENGE, consumption["continuation_challenge_id"])
                auth = self.get(
                    s.AUTHENTICATION, continuation["prerequisite_authentication_event_id"]
                )
                require(auth["challenge_consumption_id"] == consumption["challenge_consumption_id"])

    def bound_target(self, operation: Row) -> Row | None:
        if self.state_hash != operation["expected_credential_state_hash"]:
            raise c.ReviewerError("CREDENTIAL_STATE_DRIFT")
        identity = operation["target_webauthn_credential_id"]
        if operation["operation_type"] in ("REPLACE_CREDENTIAL", "REVOKE_CREDENTIAL"):
            if identity not in self.active:
                raise c.ReviewerError("TARGET_NOT_ACTIVE")
            target = self.active[identity][0]
            if target["credential_id_fingerprint"] != operation["target_credential_id_fingerprint"]:
                raise c.ReviewerError("TARGET_BINDING_MISMATCH")
            return target
        require(identity is None and operation["target_credential_id_fingerprint"] is None)
        return None

    def allowed(self) -> dict[str, tuple[bytes, bytes, int | None]]:
        require(self.principal is not None)
        return {
            identity: (
                c.decode_base64url(credential["cose_public_key_canonical"]),
                c.user_handle(
                    credential["reviewer_principal_id"], self.registration_operations[identity]
                ),
                self.counters[identity],
            )
            for identity, (credential, _event) in self.active.items()
        }
