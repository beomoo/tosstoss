from __future__ import annotations

from itertools import pairwise

import pytest
from sqlalchemy.exc import IntegrityError
from tests.backend.security_authority_test_support import (
    HASH,
    approved_issuer,
    authorization,
    business,
    candidate,
    head,
    insert,
    record,
)

from toss_dashboard_api.contracts import security_authority as c


@pytest.fixture
def pair_case(database_context):
    issuer = approved_issuer(database_context)
    with database_context.engine.begin() as connection:
        old = candidate(connection, issuer)
        initial = authorization(connection, issuer, old, "initial")
        old_rows = business(connection, old, initial, "initial")
        head(connection, old, old_rows)
        new = candidate(connection, issuer, "new", old["decision"].decision_id, "KR7000660001")
        auth_a = authorization(
            connection,
            issuer,
            old,
            "side_a",
            "SUPERSEDED",
            "event_initial",
            "link_initial",
            "intent_test",
            new["decision"].decision_id,
            10,
            11,
        )
        auth_b = authorization(
            connection,
            issuer,
            new,
            "side_b",
            "APPROVED",
            "event_initial",
            "link_initial",
            "intent_test",
            None,
            11,
            12,
        )
        rows_a = business(
            connection,
            old,
            auth_a,
            "side_a",
            "event_initial",
            "link_initial",
            "pair_test",
            persist=False,
        )
        rows_b = business(
            connection,
            new,
            auth_b,
            "side_b",
            "event_side_a",
            "link_side_a",
            "pair_test",
            persist=False,
        )
        pair = record(
            c.SupersessionPair,
            pair_id="pair_test",
            intent_id="intent_test",
            provider_id=old["binding"]["provider_id"],
            issuer_id=old["binding"]["issuer_id"],
            old_link_id="link_initial",
            old_approval_event_id="event_initial",
            old_security_id=old["binding"]["security_id"],
            old_decision_id=old["decision"].decision_id,
            old_decision_hash=old["decision"].content_hash,
            old_bundle_id=old["bundle"].bundle_id,
            old_bundle_hash=old["bundle"].content_hash,
            successor_security_id=new["binding"]["security_id"],
            successor_decision_id=new["decision"].decision_id,
            successor_decision_hash=new["decision"].content_hash,
            successor_bundle_id=new["bundle"].bundle_id,
            successor_bundle_hash=new["bundle"].content_hash,
            expected_head_hash=HASH,
            challenge_a="challenge_side_a",
            consumption_a="consumption_side_a",
            authentication_a="authentication_side_a",
            event_a="event_side_a",
            link_a="link_side_a",
            challenge_b="challenge_side_b",
            consumption_b="consumption_side_b",
            authentication_b="authentication_side_b",
            event_b="event_side_b",
            link_b="link_side_b",
        )
    return database_context, issuer, old, new, pair, rows_a, rows_b


def _complete(connection, pair, rows_a, rows_b) -> None:
    insert(connection, pair)
    for values in [rows_a, rows_b]:
        insert(connection, values["event"])
        insert(connection, values["link"])
    assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []


def test_m2_complete_pair_commits_and_two_direct_head_cas_steps(pair_case) -> None:
    context, issuer, old, new, pair, a, b = pair_case
    with context.engine.begin() as connection:
        _complete(connection, pair, a, b)
        previous = HASH
        for values in [a, b]:
            link = values["link"]
            new_hash = c.security_hash(link.link_id)
            result = connection.exec_driver_sql(
                "UPDATE security_authority_link_heads SET link_id=?,link_hash=?,security_id=?,"
                "profile_id=?,link_state=?,previous_state_hash=?,state_hash=? "
                "WHERE provider_id=? AND state_hash=?",
                (
                    link.link_id,
                    link.content_hash,
                    link.security_id,
                    link.profile_id,
                    link.link_state,
                    previous,
                    new_hash,
                    link.provider_id,
                    previous,
                ),
            )
            assert result.rowcount == 1
            previous = new_hash
        assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []
    with context.engine.connect() as connection:
        assert (
            connection.exec_driver_sql(
                "SELECT link_id FROM security_authority_link_heads"
            ).scalar_one()
            == "link_side_b"
        )


@pytest.mark.parametrize(
    "field,source",
    [
        ("old_decision_id", "successor_decision_id"),
        ("successor_decision_id", "old_decision_id"),
        ("old_bundle_id", "successor_bundle_id"),
        ("successor_bundle_id", "old_bundle_id"),
        ("old_bundle_hash", "successor_bundle_hash"),
        ("successor_bundle_hash", "old_bundle_hash"),
        ("old_security_id", "successor_security_id"),
        ("successor_security_id", "old_security_id"),
        ("challenge_a", "challenge_b"),
        ("challenge_b", "challenge_a"),
        ("consumption_a", "consumption_b"),
        ("authentication_a", "authentication_b"),
        ("event_a", "event_b"),
        ("link_a", "link_b"),
        ("old_approval_event_id", "event_a"),
        ("old_link_id", "link_a"),
    ],
)
def test_m2_wrong_pair_binding_is_rejected(pair_case, field, source) -> None:
    context, issuer, old, new, pair, a, b = pair_case
    with pytest.raises(IntegrityError):
        with context.engine.begin() as connection:
            insert(connection, pair, **{field: getattr(pair, source)})
            for values in [a, b]:
                insert(connection, values["event"])
                insert(connection, values["link"])
    with context.engine.connect() as connection:
        assert (
            connection.exec_driver_sql(
                "SELECT count(*) FROM security_supersession_pairs"
            ).scalar_one()
            == 0
        )
        assert (
            connection.exec_driver_sql(
                "SELECT count(*) FROM security_reviewer_authentication_events"
            ).scalar_one()
            == 3
        )


def test_m2_partial_pair_rejected_but_durable_auth_survives(pair_case) -> None:
    context, issuer, old, new, pair, a, b = pair_case
    with pytest.raises(IntegrityError):
        with context.engine.begin() as connection:
            insert(connection, pair)
            insert(connection, a["event"])
            insert(connection, a["link"])
            assert connection.exec_driver_sql("PRAGMA foreign_key_check").all()
    with context.engine.connect() as connection:
        assert (
            connection.exec_driver_sql(
                "SELECT count(*) FROM security_reviewer_authentication_events"
            ).scalar_one()
            == 3
        )
        assert (
            connection.exec_driver_sql("SELECT count(*) FROM security_approval_events").scalar_one()
            == 1
        )
        assert (
            connection.exec_driver_sql("SELECT count(*) FROM security_authority_links").scalar_one()
            == 1
        )
        assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []


def test_m2_business_savepoint_rollback_keeps_two_terminal_authentications(pair_case) -> None:
    context, issuer, old, new, pair, a, b = pair_case
    with context.engine.begin() as connection:
        savepoint = connection.begin_nested()
        insert(connection, pair)
        insert(connection, a["event"])
        insert(connection, a["link"])
        assert connection.exec_driver_sql("PRAGMA foreign_key_check").all()
        savepoint.rollback()
        assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []
    with context.engine.connect() as connection:
        assert (
            connection.exec_driver_sql(
                "SELECT count(*) FROM security_reviewer_authentication_events"
            ).scalar_one()
            == 3
        )
        assert (
            connection.exec_driver_sql(
                "SELECT count(*) FROM security_supersession_pairs"
            ).scalar_one()
            == 0
        )


def test_all_history_objects_reject_direct_updates_and_deletes(pair_case) -> None:
    from tests.backend.security_authority_test_support import TABLES

    context, issuer, old, new, pair, a, b = pair_case
    with context.engine.begin() as connection:
        _complete(connection, pair, a, b)
        insert(
            connection,
            record(
                c.EvidenceRelation,
                relation_id="relation_test",
                prior_evidence_id=old["evidence"].evidence_id,
                prior_evidence_hash=old["evidence"].content_hash,
                successor_evidence_id=new["evidence"].evidence_id,
                successor_evidence_hash=new["evidence"].content_hash,
                relation_kind="SUPERSEDES",
                effective_date=None,
                effective_date_missing_reason="NOT_SUPPLIED_BY_AUTHORITY",
            ),
        )
        insert(
            connection,
            record(
                c.BundleScopeResult,
                bundle_id=old["bundle"].bundle_id,
                bundle_hash=old["bundle"].content_hash,
                scope=c.Scope.SECURITY_IDENTIFIER,
                result="MISSING",
                reason_codes=("TEST_ONLY",),
                owner_application_ids=(),
            ),
        )
        insert(
            connection,
            record(
                c.BundleProviderObservation,
                bundle_id=old["bundle"].bundle_id,
                bundle_hash=old["bundle"].content_hash,
                provider_id=old["binding"]["provider_id"],
                observation_id=issuer["observation"]["observation_id"],
                observation_hash=HASH,
                member_ordinal=0,
            ),
        )
        insert(
            connection,
            record(
                c.ApprovalEvidenceObservation,
                approval_event_id=a["event"].approval_event_id,
                approval_hash=a["event"].content_hash,
                bundle_id=old["bundle"].bundle_id,
                application_id=old["application"].application_id,
                application_hash=old["application"].content_hash,
                evidence_id=old["evidence"].evidence_id,
                evidence_hash=old["evidence"].content_hash,
                observation_id=old["observation"].observation_id,
                observation_hash=old["observation"].content_hash,
                member_ordinal=0,
            ),
        )
        assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []
        for table in TABLES.values():
            assert connection.exec_driver_sql(f"SELECT count(*) FROM {table}").scalar_one() > 0
            for action in (
                ["DELETE"] if table == "security_authority_link_heads" else ["UPDATE", "DELETE"]
            ):
                sql = (
                    f"DELETE FROM {table}"
                    if action == "DELETE"
                    else f"UPDATE {table} SET payload_json=payload_json"
                )
                with pytest.raises(IntegrityError, match="trg_0008_"):
                    with connection.begin_nested():
                        connection.exec_driver_sql(sql)


def test_issuer_guard_allows_change_only_after_security_safety_transition(database_context) -> None:
    issuer = approved_issuer(database_context)
    with database_context.engine.begin() as connection:
        # With no C approved head the B writer remains usable.
        nested = connection.begin_nested()
        connection.exec_driver_sql("UPDATE issuer_authority_link_heads SET state_hash=?", (HASH,))
        nested.rollback()
        g = candidate(connection, issuer)
        auth = authorization(connection, issuer, g, "initial")
        rows = business(connection, g, auth, "initial")
        head(connection, g, rows)
        for sql, args in [
            ("DELETE FROM issuer_authority_link_heads", ()),
            ("UPDATE issuer_authority_link_heads SET state_hash=?", (HASH,)),
        ]:
            with pytest.raises(IntegrityError, match="issuer_head"):
                with connection.begin_nested():
                    connection.exec_driver_sql(sql, args)
        old = rows["link"]
        safety = record(
            c.AuthorityLink,
            **old.model_dump(
                exclude={
                    "contract_version",
                    "content_hash",
                    "audit_hash",
                    "recorded_at",
                    "link_id",
                    "link_state",
                    "approval_event_id",
                    "approval_hash",
                    "machine_trigger_decision_id",
                    "supersedes_link_id",
                }
            ),
            link_id="link_safety",
            link_state="REVIEW_REQUIRED",
            approval_event_id=None,
            approval_hash=None,
            machine_trigger_decision_id=g["decision"].decision_id,
            supersedes_link_id=old.link_id,
        )
        insert(connection, safety)
        result = connection.exec_driver_sql(
            "UPDATE security_authority_link_heads SET link_id=?,link_hash=?,link_state=?,"
            "previous_state_hash=?,state_hash=? WHERE provider_id=? AND link_id=? AND state_hash=?",
            (
                safety.link_id,
                safety.content_hash,
                "REVIEW_REQUIRED",
                HASH,
                c.security_hash("safety"),
                old.provider_id,
                old.link_id,
                HASH,
            ),
        )
        assert result.rowcount == 1
        assert (
            connection.exec_driver_sql(
                "UPDATE issuer_authority_link_heads SET state_hash=?", (HASH,)
            ).rowcount
            == 1
        )


def test_m3_counter_contract_edges_and_no_security_cursor(database_context) -> None:
    issuer = approved_issuer(database_context, registration_count=5, issuer_count=6)
    with database_context.engine.begin() as connection:
        g = candidate(connection, issuer)
        auth = authorization(connection, issuer, g, "counter", previous=6, asserted=7)[
            "authentication"
        ]
        assert (auth.previous_sign_count, auth.asserted_sign_count) == (6, 7)
        # Synthetic Security representation with the actual 5 -> 6 issuer seed.
        # The complete shared-reader path is tested in test_shared_counter_union.
        edge = connection.exec_driver_sql(
            "SELECT previous_sign_count,asserted_sign_count "
            "FROM security_reviewer_authentication_events"
        ).one()
        conceptual_edges = [("issuer", 5, 6), ("security", *edge), ("issuer", 7, 8)]
        assert [(a[2], b[1]) for a, b in pairwise(conceptual_edges)] == [(6, 6), (7, 7)]
        tables = {
            r[0]
            for r in connection.exec_driver_sql("SELECT name FROM sqlite_master WHERE type='table'")
        }
        assert not any("security" in name and "counter" in name for name in tables)
        for field, value in [
            ("previous_sign_count", 6.5),
            ("asserted_sign_count", 6),
            ("previous_sign_count", None),
        ]:
            with pytest.raises(IntegrityError):
                with connection.begin_nested():
                    insert(
                        connection,
                        auth,
                        authentication_event_id="authentication_invalid",
                        **{field: value},
                    )


def test_no_usable_counter_accepts_only_null_counts(database_context) -> None:
    issuer = approved_issuer(database_context, no_counter=True)
    with database_context.engine.begin() as connection:
        graph = candidate(connection, issuer)
        auth = authorization(connection, issuer, graph, "no_counter", previous=None, asserted=None)[
            "authentication"
        ]
        assert auth.previous_sign_count is None and auth.asserted_sign_count is None
        with pytest.raises(IntegrityError, match="CHECK constraint"):
            with connection.begin_nested():
                insert(
                    connection, auth, authentication_event_id="auth_invalid", asserted_sign_count=0
                )


def test_decision_chain_root_successor_and_fork_constraints(database_context) -> None:
    issuer = approved_issuer(database_context)
    with database_context.engine.begin() as connection:
        graph = candidate(connection, issuer)
        d = graph["decision"]
        with pytest.raises(IntegrityError, match="UNIQUE constraint"):
            with connection.begin_nested():
                insert(connection, d, decision_id="decision_second_root")
        insert(
            connection, d, decision_id="decision_successor", supersedes_decision_id=d.decision_id
        )
        with pytest.raises(IntegrityError, match="UNIQUE constraint"):
            with connection.begin_nested():
                insert(
                    connection, d, decision_id="decision_fork", supersedes_decision_id=d.decision_id
                )
        with pytest.raises(IntegrityError, match="FOREIGN KEY constraint"):
            with connection.begin_nested():
                insert(
                    connection,
                    d,
                    decision_id="decision_orphan",
                    supersedes_decision_id="decision_missing",
                )
        assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []


def test_issuer_guard_is_provider_scoped_and_issuer_wide_batch_fails_closed(
    database_context,
) -> None:
    from tests.backend.security_authority_test_support import second_provider_schema_parent

    first = approved_issuer(database_context)
    second = second_provider_schema_parent(database_context, first)
    assert first["link"]["issuer_id"] == second["link"]["issuer_id"]
    with database_context.engine.begin() as connection:
        g1 = candidate(connection, first, "first")
        a1 = authorization(connection, first, g1, "first", previous=10, asserted=11)
        rows1 = business(connection, g1, a1, "first")
        head(connection, g1, rows1)
        # Other provider is unaffected while it has no approved Security dependency.
        savepoint = connection.begin_nested()
        assert (
            connection.exec_driver_sql(
                "UPDATE issuer_authority_link_heads SET state_hash=? WHERE "
                "provider_security_identity_id=?",
                (HASH, second["link"]["provider_security_identity_id"]),
            ).rowcount
            == 1
        )
        savepoint.rollback()
        g2 = candidate(connection, second, "second")
        a2 = authorization(connection, second, g2, "second", previous=11, asserted=12)
        rows2 = business(connection, g2, a2, "second")
        head(connection, g2, rows2)
        original = connection.exec_driver_sql(
            "SELECT provider_security_identity_id,state_hash FROM "
            "issuer_authority_link_heads ORDER BY "
            "provider_security_identity_id"
        ).all()
        for graph, rows in [(g1, rows1), (g2, rows2)]:
            with pytest.raises(IntegrityError, match="issuer_head"):
                with connection.begin_nested():
                    connection.exec_driver_sql(
                        "UPDATE issuer_authority_link_heads SET state_hash=?", (HASH,)
                    )
            assert (
                connection.exec_driver_sql(
                    "SELECT provider_security_identity_id,state_hash FROM "
                    "issuer_authority_link_heads ORDER BY "
                    "provider_security_identity_id"
                ).all()
                == original
            )
            link = rows["link"]
            safety = record(
                c.AuthorityLink,
                **link.model_dump(
                    exclude={
                        "contract_version",
                        "content_hash",
                        "audit_hash",
                        "recorded_at",
                        "link_id",
                        "link_state",
                        "approval_event_id",
                        "approval_hash",
                        "machine_trigger_decision_id",
                        "supersedes_link_id",
                    }
                ),
                link_id=link.link_id + "_safety",
                link_state="REVIEW_REQUIRED",
                approval_event_id=None,
                approval_hash=None,
                machine_trigger_decision_id=graph["decision"].decision_id,
                supersedes_link_id=link.link_id,
            )
            insert(connection, safety)
            assert (
                connection.exec_driver_sql(
                    "UPDATE security_authority_link_heads SET "
                    "link_id=?,link_hash=?,link_state=?,previous_state_hash=?,state_hash=?"
                    " WHERE provider_id=? AND link_id=? AND state_hash=?",
                    (
                        safety.link_id,
                        safety.content_hash,
                        "REVIEW_REQUIRED",
                        HASH,
                        c.security_hash(safety.link_id),
                        link.provider_id,
                        link.link_id,
                        HASH,
                    ),
                ).rowcount
                == 1
            )
        assert (
            connection.exec_driver_sql(
                "UPDATE issuer_authority_link_heads SET state_hash=?", (HASH,)
            ).rowcount
            == 2
        )


def test_approval_and_link_predecessors_cannot_fork(database_context) -> None:
    issuer = approved_issuer(database_context)
    with database_context.engine.begin() as connection:
        graph = candidate(connection, issuer)
        auth = authorization(connection, issuer, graph, "root")
        root = business(connection, graph, auth, "root")
        revoked_auth = authorization(
            connection,
            issuer,
            graph,
            "revoke",
            "REVOKED",
            "event_root",
            "link_root",
            previous=10,
            asserted=11,
        )
        revoked = business(connection, graph, revoked_auth, "revoke", "event_root", "link_root")
        fork_auth = authorization(
            connection,
            issuer,
            graph,
            "fork",
            "REVOKED",
            "event_root",
            "link_root",
            previous=11,
            asserted=12,
        )
        fork = business(
            connection, graph, fork_auth, "fork", "event_root", "link_root", persist=False
        )
        with pytest.raises(IntegrityError, match="UNIQUE constraint"):
            with connection.begin_nested():
                insert(connection, fork["event"])
        with pytest.raises(IntegrityError, match="UNIQUE constraint"):
            with connection.begin_nested():
                insert(connection, root["link"], link_id="link_second_root")
        with pytest.raises(IntegrityError, match="UNIQUE constraint"):
            with connection.begin_nested():
                insert(connection, revoked["link"], link_id="link_fork")
        assert (
            connection.exec_driver_sql(
                "SELECT count(*) FROM security_reviewer_authentication_events"
            ).scalar_one()
            == 3
        )
        assert (
            connection.exec_driver_sql("SELECT count(*) FROM security_approval_events").scalar_one()
            == 2
        )
