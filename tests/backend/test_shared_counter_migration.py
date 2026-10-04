"""Real Alembic 0010 boundaries; all Security authorization rows are synthetic."""

import json
import sqlite3
from contextlib import closing
from pathlib import Path
from runpy import run_path

import pytest
from alembic import command
from sqlalchemy import event
from sqlalchemy.engine import Engine
from tests.backend.conftest import alembic_config
from tests.backend.test_identifier_migration_atomicity import _reopened as _reopen
from tests.backend.test_shared_counter_union import ledger, security_edge
from tests.backend.test_shared_counter_union import shared as shared_fixture

from toss_dashboard_api.reviewer import canonical as c

REVISION = "0010_phase_02_cp3_c3_shared_counter_union"
shared = shared_fixture
PREVIOUS = "0009_phase_02_cp3_c2_c3_identifier_claim_contract"
MIGRATION = (
    Path(__file__).resolve().parents[2] / "services/api/alembic/versions" / (REVISION + ".py")
)


def db_path(state):
    return Path(state.context.url.removeprefix("sqlite:///"))


def test_upgrade_downgrade_reupgrade_exact_sql_history(shared, record_property):
    state = shared()
    cfg = alembic_config(state.context.url)
    after = _reopen(db_path(state))
    command.downgrade(cfg, PREVIOUS)
    before = _reopen(db_path(state))
    migration = run_path(str(MIGRATION))
    with state.context.engine.connect() as conn:
        for name, sql in migration["_OLD"]:
            assert (
                conn.exec_driver_sql(
                    "SELECT sql FROM sqlite_master WHERE name=?", (name,)
                ).scalar_one()
                == sql
            )
    command.upgrade(cfg, REVISION)
    assert _reopen(db_path(state)) == after
    assert {k: v for k, v in before["tables"].items() if k != "alembic_version"} == {
        k: v for k, v in after["tables"].items() if k != "alembic_version"
    }
    assert ledger(state).counters[state.authenticator.identity] == 6
    record_property("reopen_roundtrip", json.dumps({"before": before, "after": after}))


@pytest.mark.parametrize("numeric", [True, False])
def test_downgrade_security_history_policy(shared, numeric, record_property):
    state = shared() if numeric else shared(0, 0)
    security_edge(state, "downgrade", 6 if numeric else None, 7 if numeric else None)
    before = _reopen(db_path(state))
    cfg = alembic_config(state.context.url)
    if numeric:
        with pytest.raises(RuntimeError, match="accepted numeric Security history"):
            command.downgrade(cfg, PREVIOUS)
        assert _reopen(db_path(state)) == before
    else:
        command.downgrade(cfg, PREVIOUS)
        command.upgrade(cfg, REVISION)
        assert _reopen(db_path(state)) == before
    record_property("downgrade_reopen", json.dumps(before))


@pytest.mark.parametrize("previous,asserted", [(6, 8), (5, 7), (99, 100), (0, 100)])
def test_existing_corrupt_graph_reader_and_upgrade_fail_closed(
    shared, previous, asserted, record_property
):
    state = shared()
    cfg = alembic_config(state.context.url)
    command.downgrade(cfg, PREVIOUS)
    security_edge(state, "first", 6, 7)
    security_edge(state, "bad", previous, asserted)
    before = _reopen(db_path(state))
    with pytest.raises(c.LedgerCorruption):
        ledger(state)
    with pytest.raises(c.LedgerCorruption):
        command.upgrade(cfg, REVISION)
    assert _reopen(db_path(state)) == before
    record_property("malformed_history_reopen", json.dumps(before))


@pytest.mark.parametrize("direction", ["upgrade", "downgrade"])
@pytest.mark.parametrize("point", ["pre_change", "after_drop", "after_create", "revision_update"])
@pytest.mark.parametrize("error_type", [RuntimeError, KeyboardInterrupt])
def test_atomic_fault_reopen(shared, direction, point, error_type, record_property):
    state = shared()
    cfg = alembic_config(state.context.url)
    if direction == "upgrade":
        command.downgrade(cfg, PREVIOUS)
    before = _reopen(db_path(state))
    progress = {"injected": 0, "drops": 0, "creates": 0}

    def fault(conn, cursor, statement, parameters, context, executemany):
        trigger_drop = statement.startswith("DROP TRIGGER ")
        trigger_create = statement.startswith("CREATE TRIGGER ")
        revision_update = statement.startswith("UPDATE alembic_version SET")
        hit = (
            (point == "pre_change" and trigger_drop and progress["drops"] == 0)
            or (point == "after_drop" and trigger_drop and progress["drops"] == 1)
            or (point == "after_create" and trigger_create and progress["creates"] == 1)
            or (point == "revision_update" and revision_update)
        )
        if hit:
            progress["injected"] += 1
            assert conn.connection.driver_connection.in_transaction
            raise error_type("synthetic 0010 boundary failure")
        progress["drops"] += int(trigger_drop)
        progress["creates"] += int(trigger_create)

    event.listen(Engine, "before_cursor_execute", fault)
    try:
        with pytest.raises(error_type, match="synthetic 0010 boundary failure"):
            if direction == "upgrade":
                command.upgrade(cfg, REVISION)
            else:
                command.downgrade(cfg, PREVIOUS)
    finally:
        event.remove(Engine, "before_cursor_execute", fault)
    assert progress["injected"] == 1
    after = _reopen(db_path(state))
    assert after == before
    record_property(
        "atomic_reopen",
        json.dumps(
            {
                "direction": direction,
                "point": point,
                "error": error_type.__name__,
                "progress": progress,
                "before": before,
                "after": after,
            }
        ),
    )
    if direction == "upgrade":
        command.upgrade(cfg, REVISION)
    else:
        command.downgrade(cfg, PREVIOUS)
    assert ledger(state).counters[state.authenticator.identity] == 6


def test_exact_predecessor_schema_drift_refused(shared):
    state = shared()
    cfg = alembic_config(state.context.url)
    command.downgrade(cfg, PREVIOUS)
    # An extra schema object is drift. No guard is removed or weakened.
    with closing(sqlite3.connect(db_path(state))) as conn:
        conn.execute("CREATE INDEX synthetic_drift ON reviewer_webauthn_credentials (rp_id)")
    before = _reopen(db_path(state))
    with pytest.raises(RuntimeError, match="exact predecessor schema mismatch"):
        command.upgrade(cfg, REVISION)
    assert _reopen(db_path(state)) == before


def test_valid_existing_security_history_upgrades_without_rewrite(shared):
    state = shared()
    cfg = alembic_config(state.context.url)
    command.downgrade(cfg, PREVIOUS)
    security_edge(state, "existing_valid", 6, 7)
    before = _reopen(db_path(state))
    command.upgrade(cfg, REVISION)
    after = _reopen(db_path(state))
    assert {k: v for k, v in before["tables"].items() if k != "alembic_version"} == {
        k: v for k, v in after["tables"].items() if k != "alembic_version"
    }
    assert ledger(state).counters[state.authenticator.identity] == 7


@pytest.mark.parametrize("direction", ["upgrade", "downgrade"])
def test_real_revision_update_abort_reopen(shared, direction, record_property):
    from sqlalchemy.exc import IntegrityError

    state = shared()
    cfg = alembic_config(state.context.url)
    if direction == "upgrade":
        command.downgrade(cfg, PREVIOUS)
    with closing(sqlite3.connect(db_path(state))) as conn:
        conn.execute(
            "CREATE TRIGGER synthetic_revision_abort BEFORE UPDATE ON alembic_version "
            "BEGIN SELECT RAISE(ABORT, 'synthetic revision update failure'); END"
        )
    before = _reopen(db_path(state))
    with pytest.raises(IntegrityError, match="synthetic revision update failure"):
        if direction == "upgrade":
            command.upgrade(cfg, REVISION)
        else:
            command.downgrade(cfg, PREVIOUS)
    after = _reopen(db_path(state))
    assert before == after
    record_property(
        "real_revision_abort",
        json.dumps({"direction": direction, "before": before, "after": after}),
    )
