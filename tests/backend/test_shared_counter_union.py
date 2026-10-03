"""0010: real R1 runtime/software signatures; SYNTHETIC Security schema rows.

No physical authenticator, real OWNER qualification, or C3 disposition runtime.
"""

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import timedelta
from threading import Barrier, Event
from types import SimpleNamespace

import pytest
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError
from tests.backend import security_authority_test_support as support
from tests.backend.reviewer_test_support import Authenticator, Clock
from tests.backend.test_authority_decision_engine import EVALUATED_AT, _kr_harness, _kr_request
from tests.backend.test_reviewer_runtime import OWNER, enroll

from toss_dashboard_api.contracts import security_authority as sc
from toss_dashboard_api.reviewer import canonical as c
from toss_dashboard_api.reviewer.issuer_disposition import (
    IssuerDispositionError,
    IssuerDispositionService,
)
from toss_dashboard_api.reviewer.ledger import Ledger
from toss_dashboard_api.reviewer.runtime import Ceremony, _Runtime


@pytest.fixture
def shared(database_context):
    def build(registration=5, bootstrap=7):
        context = database_context
        harness = _kr_harness(context)
        ready = harness.engine.evaluate(_kr_request(harness))
        clock = Clock(EVALUATED_AT + timedelta(minutes=1))
        runtime = _Runtime(context.engine, lambda: OWNER, clock)
        authenticator = Authenticator()
        enroll(runtime, authenticator, registration_count=registration, assertion_count=bootstrap)
        service = IssuerDispositionService(runtime, harness.engine)
        challenge = service.issue(ready.decision.issuer_decision_id, "APPROVED")
        first = 0 if registration == bootstrap == 0 else (registration or bootstrap) + 1
        service.complete(
            challenge.challenge_id,
            authenticator.assertion(challenge.options, first),
            structured_reason_code="VERIFIED_EXACT_AUTHORITY",
            review_note="SYNTHETIC M3 test",
        )
        with context.engine.begin() as connection:
            issuer = {}
            for key, table in (
                ("link", "issuer_authority_links"),
                ("head", "issuer_authority_link_heads"),
                ("principal", "reviewer_principals"),
                ("credential", "reviewer_webauthn_credentials"),
            ):
                issuer[key] = dict(
                    connection.exec_driver_sql(f"SELECT * FROM {table}").mappings().one()
                )
            issuer["observation"] = dict(
                connection.exec_driver_sql("SELECT * FROM provider_security_master_observations")
                .mappings()
                .first()
            )
            graph = support.candidate(connection, issuer, "shared", persist_subjects=False)
        return SimpleNamespace(
            context=context,
            runtime=runtime,
            clock=clock,
            authenticator=authenticator,
            service=service,
            issuer=issuer,
            graph=graph,
        )

    return build


def security_edge(state, suffix, previous, asserted, *, connection=None, **changes):
    def insert(conn):
        return support.authorization(
            conn,
            state.issuer,
            state.graph,
            suffix,
            previous=previous,
            asserted=asserted,
            authentication_policy_version=c.POLICY,
            **changes,
        )

    if connection is not None:
        return insert(connection)
    with state.context.engine.begin() as conn:
        return insert(conn)


def ledger(state):
    with state.context.engine.connect() as connection:
        return Ledger(connection, OWNER)


def issuer_auth(state, asserted):
    state.clock.value += timedelta(seconds=1)
    challenge = state.service.issue_revocation(
        state.issuer["link"]["provider_security_identity_id"]
    )
    # Only authenticate, using the actual shared Ledger. No C3 business service.
    from sqlalchemy.orm import Session

    with state.context.engine.connect() as connection:
        connection.exec_driver_sql("BEGIN IMMEDIATE")
        with Session(bind=connection) as session:
            _, authentication, _, failure = state.service._consume(
                session,
                connection,
                Ledger(connection, OWNER),
                challenge.challenge_id,
                state.authenticator.assertion(challenge.options, asserted),
            )
            assert authentication is not None and failure is None
        connection.commit()
    return challenge


def lifecycle(state, operation, asserted):
    state.clock.value += timedelta(seconds=1)
    target = (
        {}
        if operation == "ADD_CREDENTIAL"
        else {"target_webauthn_credential_id": state.authenticator.identity}
    )
    challenge = state.runtime.issue(operation, **target)
    result = state.runtime.complete(
        challenge.challenge_id, state.authenticator.assertion(challenge.options, asserted)
    )
    new = None
    if operation != "REVOKE_CREDENTIAL":
        assert isinstance(result, Ceremony)
        new = Authenticator()
        result = state.runtime.complete(result.challenge_id, new.registration(result.options, 5))
    assert result.result == "SUCCEEDED"
    return challenge, new


def test_original_5_6_7_8_natural_reader_and_security_again(shared):
    state = shared()
    assert ledger(state).counters[state.authenticator.identity] == 6
    security_edge(state, "first", 6, 7)
    assert ledger(state).counters[state.authenticator.identity] == 7
    issuer_auth(state, 8)
    security_edge(state, "second", 8, 19)  # Strict increase, never an invented +1 rule.
    assert ledger(state).counters[state.authenticator.identity] == 19
    with state.context.engine.connect() as connection:
        assert connection.exec_driver_sql(
            "SELECT previous_sign_count,asserted_sign_count "
            "FROM reviewer_authentication_events ORDER BY asserted_sign_count"
        ).all() == [(5, 6), (7, 8)]
        assert (
            connection.exec_driver_sql("SELECT count(*) FROM security_approval_events").scalar_one()
            == 0
        )


@pytest.mark.parametrize("operation", ["ADD_CREDENTIAL", "REPLACE_CREDENTIAL", "REVOKE_CREDENTIAL"])
def test_security_then_actual_lifecycle_preserves_history(shared, operation):
    state = shared()
    security_edge(state, "before_lifecycle", 6, 7)
    pending = None
    if operation != "ADD_CREDENTIAL":
        pending = state.service.issue_revocation(
            state.issuer["link"]["provider_security_identity_id"]
        )
    _, new = lifecycle(state, operation, 11)
    snapshot = ledger(state)
    assert snapshot.counters[state.authenticator.identity] == 11
    assert len(snapshot.security_authentications) == 1
    if operation == "ADD_CREDENTIAL":
        security_edge(state, "after_lifecycle", 11, 13)
        assert ledger(state).counters[state.authenticator.identity] == 13
    else:
        assert state.authenticator.identity not in snapshot.active
        assert pending is not None
        rejected_code = (
            "EMPTY_OR_INVALID_ALLOW_CREDENTIALS"
            if operation == "REVOKE_CREDENTIAL"
            else "CREDENTIAL_ID_MISMATCH"
        )
        with pytest.raises(IssuerDispositionError, match=rejected_code):
            state.service.complete(
                pending.challenge_id,
                state.authenticator.assertion(pending.options, 12),
                structured_reason_code="VERIFIED_EXACT_AUTHORITY",
                review_note="SYNTHETIC retired credential rejection",
            )
        if new is not None:
            challenge = state.runtime.issue("ADD_CREDENTIAL")
            with pytest.raises(c.ReviewerError, match="CREDENTIAL_ID_MISMATCH"):
                state.runtime.complete(
                    challenge.challenge_id, state.authenticator.assertion(challenge.options, 12)
                )
        else:
            with pytest.raises(c.ReviewerError, match="FIRST_ENROLLMENT_PERMANENTLY_CLOSED"):
                state.runtime.issue("FIRST_ENROLLMENT")
        assert ledger(state).counters[state.authenticator.identity] == 11


def test_registration_security_issuer_security(shared):
    state = shared()
    _, new = lifecycle(state, "ADD_CREDENTIAL", 7)
    state.authenticator = new
    with state.context.engine.connect() as connection:
        state.issuer["credential"] = dict(
            connection.exec_driver_sql(
                "SELECT * FROM reviewer_webauthn_credentials WHERE webauthn_credential_id=?",
                (new.identity,),
            )
            .mappings()
            .one()
        )
    security_edge(state, "new_credential", 5, 15)
    issuer_auth(state, 20)
    security_edge(state, "new_again", 20, 30)
    assert ledger(state).counters[new.identity] == 30


@pytest.mark.parametrize("registration,bootstrap", [(5, 7), (0, 7), (0, 0)])
def test_bootstrap_and_null_capability_all_domains_single_use(shared, registration, bootstrap):
    state = shared(registration, bootstrap)
    null = registration == bootstrap == 0
    before = ledger(state).counters[state.authenticator.identity]
    edge = security_edge(state, "capability", before, None if null else before + 3)
    with state.context.engine.begin() as connection:
        with pytest.raises(IntegrityError):
            with connection.begin_nested():
                support.insert(connection, edge["consumption"], consumption_id="consumption_replay")
    issuer_auth(state, 0 if null else before + 7)
    challenge, _ = lifecycle(state, "ADD_CREDENTIAL", 0 if null else before + 9)
    with pytest.raises(c.ReviewerError):
        state.runtime.complete(
            challenge.challenge_id,
            state.authenticator.assertion(challenge.options, 0 if null else before + 10),
        )
    assert ledger(state).counters[state.authenticator.identity] == (None if null else before + 9)
    if null:
        with state.context.engine.connect() as connection:
            for table in (
                "reviewer_authentication_events",
                "reviewer_credential_operation_authentication_events",
                "security_reviewer_authentication_events",
            ):
                assert all(
                    tuple(row) == (None, None)
                    for row in connection.exec_driver_sql(
                        f"SELECT previous_sign_count,asserted_sign_count FROM {table}"
                    )
                )


NEGATIVE_EDGES = [(6, 12), (5, 12), (4, 12), (7, 7), (6, 7), (99, 100), (0, 100)]


@contextmanager
def malformed_insert(engine, table, transform):
    """Inject a synthetic bad row at the SQL boundary; keep every DB guard ON."""
    calls = []

    def alter(conn, cursor, statement, parameters, context, executemany):
        if statement.startswith("INSERT INTO " + table + " "):
            names = statement.split("(", 1)[1].split(")", 1)[0].replace(" ", "").split(",")
            row = dict(zip(names, parameters, strict=True))
            transform(row)
            calls.append(row)
            return statement, tuple(row[name] for name in names)
        return statement, parameters

    event.listen(engine, "before_cursor_execute", alter, retval=True)
    try:
        yield calls
    finally:
        event.remove(engine, "before_cursor_execute", alter)


@pytest.mark.parametrize("domain", ["issuer", "lifecycle", "security"])
@pytest.mark.parametrize("case", ["wrong_capability", "supported_null", "null_numeric"])
def test_db_capability_matrix(shared, domain, case):
    state = shared(0, 0) if case == "null_numeric" else shared()
    null = case == "null_numeric"
    table = {
        "issuer": "reviewer_authentication_events",
        "lifecycle": "reviewer_credential_operation_authentication_events",
        "security": "security_reviewer_authentication_events",
    }[domain]

    def corrupt(row):
        if case == "wrong_capability":
            row["counter_capability"] = "UNSUPPORTED"
        elif case == "supported_null":
            row.update(previous_sign_count=None, asserted_sign_count=None)
        else:
            row.update(previous_sign_count=0, asserted_sign_count=1)

    with malformed_insert(state.context.engine, table, corrupt) as calls:
        expected = c.ReviewerError if domain == "lifecycle" else IntegrityError
        with pytest.raises(expected) as failure:
            if domain == "issuer":
                issuer_auth(state, 0 if null else 10)
            elif domain == "lifecycle":
                lifecycle(state, "ADD_CREDENTIAL", 0 if null else 10)
            else:
                security_edge(state, "capability_bad", None if null else 6, None if null else 10)
        if domain == "lifecycle":
            assert failure.value.code == "REVIEWER_TRANSACTION_FAILED"
    assert len(calls) == 1
    assert ledger(state).counters[state.authenticator.identity] == (None if null else 6)


@pytest.mark.parametrize(
    "case",
    [
        "credential_binding",
        "capability",
        "content_hash",
        "audit_hash",
        "contract_version",
        "policy_version",
        "consumption_binding",
        "challenge_binding",
        "failed_authentication",
        "failed_consumption",
        "unverified_flag",
    ],
)
def test_reader_persisted_security_admission_fails_closed(shared, case):
    state = shared()

    def corrupt(row):
        data = sc.strict_security_json(row["payload_json"])
        key, value = {
            "credential_binding": ("credential_id_fingerprint", c.digest(b"wrong")),
            "capability": ("counter_capability", "UNKNOWN"),
            "content_hash": ("content_hash", c.digest(b"wrong")),
            "audit_hash": ("audit_hash", c.digest(b"wrong")),
            "contract_version": ("contract_version", "security-reviewer-authentication/9.0.0"),
            "policy_version": ("authentication_policy_version", "unsupported/9"),
            "consumption_binding": ("consumption_hash", c.digest(b"wrong")),
            "challenge_binding": ("challenge_hash", c.digest(b"wrong")),
            "failed_authentication": ("authentication_result", "REJECTED"),
            "failed_consumption": ("consumption_result", "FAILED"),
            "unverified_flag": ("signature_verified", 0),
        }[case]
        data[key] = value
        if case == "policy_version":
            # Valid content/audit hashes and exact stored scalar projection:
            # admission, not a hash mismatch, must reject the unknown profile.
            fields = {k: v for k, v in data.items() if k not in {"content_hash", "audit_hash"}}
            fields["recorded_at"] = support.NOW
            fields["authenticated_at"] = support.NOW
            sealed = sc.seal_security_record(sc.AuthenticationEvent, **fields)
            row.update(support.row(sealed))
        else:
            row["payload_json"] = sc.canonical_security_bytes(data).decode()

    with malformed_insert(
        state.context.engine, "security_reviewer_authentication_events", corrupt
    ) as calls:
        security_edge(state, "persisted_bad", 6, 7)
    assert len(calls) == 1
    with state.context.engine.connect() as connection:
        assert (
            connection.exec_driver_sql(
                "SELECT count(*) FROM security_reviewer_authentication_events"
            ).scalar_one()
            == 1
        )
        assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []
    with pytest.raises(c.LedgerCorruption):
        ledger(state)


@pytest.mark.parametrize(
    "case", ["duplicate", "wrong_root", "zero_asserted", "null_capability_numeric"]
)
def test_bootstrap_bad_projection_rejected_after_security(shared, case):
    state = shared(0, 7)
    security_edge(state, "after_bootstrap", 8, 9)
    with state.context.engine.begin() as conn:
        row = dict(
            conn.exec_driver_sql("SELECT * FROM reviewer_webauthn_counter_capability_assertions")
            .mappings()
            .one()
        )
        row["counter_capability_assertion_id"] = "synthetic_bad_bootstrap"
        if case == "wrong_root":
            row["previous_sign_count"] = 9
            row["asserted_sign_count"] = 10
        elif case == "zero_asserted":
            row["asserted_sign_count"] = 0
        elif case == "null_capability_numeric":
            row["selected_counter_capability"] = "NO_USABLE_COUNTER"
        with pytest.raises(IntegrityError):
            with conn.begin_nested():
                conn.exec_driver_sql(
                    "INSERT INTO reviewer_webauthn_counter_capability_assertions ("
                    + ",".join(row)
                    + ") VALUES ("
                    + ",".join("?" for _ in row)
                    + ")",
                    tuple(row.values()),
                )
    assert ledger(state).counters[state.authenticator.identity] == 9


@pytest.mark.parametrize("domain", ["issuer", "lifecycle", "security"])
@pytest.mark.parametrize(
    "previous,asserted",
    NEGATIVE_EDGES,
    ids=[
        "stale",
        "historical_nonleaf",
        "unknown",
        "duplicate_asserted",
        "fork",
        "disconnected_high",
        "second_root",
    ],
)
def test_db_negative_graph_matrix(shared, domain, previous, asserted):
    state = shared()
    security_edge(state, "existing", 6, 7)
    if domain == "security" and asserted > previous:
        with pytest.raises(IntegrityError):
            security_edge(state, "invalid", previous, asserted)
    else:
        # A deliberately malformed INSERT at the DB boundary tests the guard
        # independently of the real runtime's earlier cryptographic checks.
        table = {
            "issuer": "reviewer_authentication_events",
            "lifecycle": "reviewer_credential_operation_authentication_events",
            "security": "security_reviewer_authentication_events",
        }[domain]

        def malformed(conn, cursor, statement, parameters, context, executemany):
            if statement.startswith("INSERT INTO " + table + " "):
                names = statement.split("(", 1)[1].split(")", 1)[0].replace(" ", "").split(",")
                values = list(parameters)
                values[names.index("previous_sign_count")] = previous
                values[names.index("asserted_sign_count")] = asserted
                return statement, tuple(values)
            return statement, parameters

        event.listen(state.context.engine, "before_cursor_execute", malformed, retval=True)
        try:
            expected = c.ReviewerError if domain == "lifecycle" else IntegrityError
            with pytest.raises(expected) as failure:
                if domain == "issuer":
                    issuer_auth(state, 12)
                elif domain == "lifecycle":
                    lifecycle(state, "ADD_CREDENTIAL", 12)
                else:
                    security_edge(state, "invalid", 7, 12)
            if domain == "lifecycle":
                assert failure.value.code == "REVIEWER_TRANSACTION_FAILED"
        finally:
            event.remove(state.context.engine, "before_cursor_execute", malformed)
    assert ledger(state).counters[state.authenticator.identity] == 7


def test_separate_connection_race_and_fresh_retry(shared):
    state = shared()
    barrier = Barrier(2)

    def writer(suffix, value):
        with state.context.engine.connect() as connection:
            assert Ledger(connection, OWNER).counters[state.authenticator.identity] == 6
            connection.commit()
            barrier.wait(timeout=10)
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            try:
                security_edge(state, suffix, 6, value, connection=connection)
                connection.commit()
                return value
            except IntegrityError:
                connection.rollback()
                return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(writer, "race_a", 8)
        b = pool.submit(writer, "race_b", 9)
        results = [a.result(timeout=30), b.result(timeout=30)]
    accepted = [value for value in results if value is not None]
    assert len(accepted) == 1
    current = ledger(state).counters[state.authenticator.identity]
    assert current == accepted[0]
    security_edge(state, "fresh_retry", current, 20)
    assert ledger(state).counters[state.authenticator.identity] == 20


@pytest.mark.parametrize("first", ["issuer", "security"])
def test_issuer_security_race_and_fresh_issuer_retry(shared, first):
    from sqlalchemy.orm import Session

    state = shared()
    challenge = state.service.issue_revocation(
        state.issuer["link"]["provider_security_identity_id"]
    )
    response = state.authenticator.assertion(challenge.options, 7)
    barrier = Barrier(2)
    first_locked = Event()

    def writer(domain):
        with state.context.engine.connect() as connection:
            assert Ledger(connection, OWNER).counters[state.authenticator.identity] == 6
            connection.commit()
            barrier.wait(timeout=10)
            if domain != first:
                assert first_locked.wait(timeout=10)
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            if domain == first:
                first_locked.set()
            try:
                if domain == "issuer":
                    with Session(bind=connection) as session:
                        _, authentication, _, failure = state.service._consume(
                            session,
                            connection,
                            Ledger(connection, OWNER),
                            challenge.challenge_id,
                            response,
                        )
                        if authentication is None:
                            assert isinstance(failure, IssuerDispositionError)
                            assert str(failure) == "COUNTER_DID_NOT_ADVANCE"
                            connection.commit()
                            return None
                else:
                    security_edge(state, "cross_race", 6, 8, connection=connection)
                connection.commit()
                return domain
            except (IntegrityError, IssuerDispositionError):
                connection.rollback()
                return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(writer, "issuer")
        b = pool.submit(writer, "security")
        results = [a.result(timeout=30), b.result(timeout=30)]
    assert len([item for item in results if item is not None]) == 1
    assert first in results
    assert ledger(state).counters[state.authenticator.identity] in (7, 8)
    issuer_auth(state, 20)
    assert ledger(state).counters[state.authenticator.identity] == 20
