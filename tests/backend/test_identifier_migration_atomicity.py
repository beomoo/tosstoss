"""Real Alembic step failures on synthetic linked history, never WebAuthn evidence."""

import hashlib
import json
import shutil
import sqlite3
from contextlib import closing, contextmanager
from types import SimpleNamespace

import pytest
from alembic import command
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.pool import Pool
from tests.backend.conftest import (
    FIXTURE_DIR,
    alembic_config,
    managed_workspace_test_directory,
)
from tests.backend.security_authority_test_support import (
    approved_issuer,
    authorization,
    business,
    candidate,
    head,
    insert,
)
from tests.backend.test_identifier_claim_contract_migration import PREVIOUS, REVISION
from tests.backend.test_security_authority_remediation import reseal

from toss_dashboard_api.fixtures.importer import FixtureImporter
from toss_dashboard_api.repositories.fixture import FixtureRepository
from toss_dashboard_api.storage.database import create_database_engine, session_factory

TABLE = "security_identifier_claims"


def _hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=repr).encode()).hexdigest()


def _snapshot(db):
    objects = db.execute(
        "SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name"
    ).fetchall()
    data = {}
    for (name,) in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
        quoted = '"' + name.replace('"', '""') + '"'
        data[name] = sorted(db.execute("SELECT * FROM " + quoted).fetchall(), key=repr)
    return {
        "schema": _hash(objects),
        "objects": [(row[0], row[1], row[2], _hash(row[3])) for row in objects],
        "tables": {name: {"rows": len(rows), "sha256": _hash(rows)} for name, rows in data.items()},
        "revision": data["alembic_version"],
        "temp": db.execute("SELECT type,name FROM sqlite_temp_master ORDER BY name").fetchall(),
    }


def _reopened(path):
    with closing(sqlite3.connect(path)) as db, db:
        db.execute("PRAGMA foreign_keys=ON")
        assert db.execute("PRAGMA foreign_keys").fetchone() == (1,)
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
        return _snapshot(db)


@pytest.fixture(scope="module")
def migration_images():
    with managed_workspace_test_directory() as directory:
        old = directory / "old.sqlite3"
        url = f"sqlite:///{old.as_posix()}"
        command.upgrade(alembic_config(url), PREVIOUS)
        engine = create_database_engine(url)
        try:
            FixtureImporter(session_factory(engine)).import_repository(
                FixtureRepository(FIXTURE_DIR)
            )
            issuer = approved_issuer(SimpleNamespace(engine=engine))
            with engine.begin() as conn:
                graph = candidate(conn, issuer)
                insert(
                    conn,
                    reseal(
                        graph["identifier"],
                        claim_id="legacy_sec_history",
                        identifier_kind="SEC_REGISTERED_CLASS",
                    ),
                )
                auth = authorization(conn, issuer, graph, "atomicity")
                head(conn, graph, business(conn, graph, auth, "atomicity"))
                assert conn.exec_driver_sql("PRAGMA foreign_key_check").all() == []
        finally:
            engine.dispose()
        new = directory / "new.sqlite3"
        shutil.copyfile(old, new)
        command.upgrade(alembic_config(f"sqlite:///{new.as_posix()}"), REVISION)
        snapshots = {"old": _reopened(old), "new": _reopened(new)}
        assert snapshots["old"]["tables"][TABLE]["rows"] == 2
        for table in ("security_authority_profiles", "security_authority_links"):
            assert snapshots["old"]["tables"][table]["rows"] == 1
        assert {k: v for k, v in snapshots["old"]["tables"].items() if k != "alembic_version"} == {
            k: v for k, v in snapshots["new"]["tables"].items() if k != "alembic_version"
        }
        yield {"old": old, "new": new, "snapshots": snapshots}


def _case(images, directory, direction):
    start, target = ("old", "new") if direction == "upgrade" else ("new", "old")
    path = directory / "case.sqlite3"
    shutil.copyfile(images[start], path)
    cfg = alembic_config(f"sqlite:///{path.as_posix()}")
    operation = command.upgrade if direction == "upgrade" else command.downgrade
    destination = REVISION if direction == "upgrade" else PREVIOUS
    return (
        path,
        cfg,
        operation,
        destination,
        images["snapshots"][start],
        images["snapshots"][target],
    )


def _record(record_property, key, value):
    record_property("identifier_atomicity_" + key, json.dumps(value, sort_keys=True))


@contextmanager
def _observe_disposal():
    observations = []
    connections = []

    def observe(db, record):
        connections.append(db)
        observations.append(
            {
                "snapshot": _snapshot(db),
                "foreign_keys": db.execute("PRAGMA foreign_keys").fetchone()[0],
                "native_transaction": db.in_transaction,
            }
        )

    event.listen(Pool, "close", observe)
    try:
        yield observations
    finally:
        event.remove(Pool, "close", observe)
        assert connections
        for db in connections:
            with pytest.raises(sqlite3.ProgrammingError):
                db.execute("SELECT 1")


@pytest.mark.parametrize("direction", ["upgrade", "downgrade"])
def test_normal_step_restores_same_connection_and_preserves_history(
    migration_images,
    workspace_tmp_path,
    record_testsuite_property,
    direction,
):
    path, cfg, operation, destination, before, target = _case(
        migration_images, workspace_tmp_path, direction
    )
    with _observe_disposal() as physical:
        operation(cfg, destination)
    assert physical == [{"snapshot": target, "foreign_keys": 1, "native_transaction": False}]
    assert _reopened(path) == target
    _record(
        record_testsuite_property,
        f"{direction}_normal",
        {
            "before": before,
            "same_physical_before_close": physical,
            "after_reopen": target,
        },
    )


# Selected boundaries, not a claim to every exception/phase Cartesian product.
FAULTS = [
    ("before_copy", "RuntimeError"),
    ("after_copy", "RuntimeError"),
    ("after_copy", "KeyboardInterrupt"),
    ("after_copy", "SystemExit"),
    ("after_drop", "RuntimeError"),
    ("after_drop", "OperationalError"),
    ("after_drop", "KeyboardInterrupt"),
    ("after_drop", "SystemExit"),
    ("after_create", "RuntimeError"),
    ("after_create", "KeyboardInterrupt"),
    ("after_create", "SystemExit"),
    ("after_rows", "IntegrityError"),
    ("after_rows", "KeyboardInterrupt"),
    ("after_rows", "SystemExit"),
    ("after_restore", "RuntimeError"),
    ("after_restore", "KeyboardInterrupt"),
    ("after_restore", "SystemExit"),
    ("final_check", "OperationalError"),
    ("before_commit", "RuntimeError"),
    ("before_commit", "OperationalError"),
    ("before_commit", "KeyboardInterrupt"),
    ("before_commit", "SystemExit"),
    ("fk_cleanup", "RuntimeError"),
    ("fk_cleanup", "KeyboardInterrupt"),
    ("fk_cleanup", "SystemExit"),
    ("commit_acknowledgment", "OperationalError"),
    ("commit_acknowledgment", "SystemExit"),
    ("rollback_cleanup", "OperationalError"),
]


@pytest.mark.parametrize("direction", ["upgrade", "downgrade"])
@pytest.mark.parametrize("phase,error_name", FAULTS)
def test_atomic_fault_matrix(
    migration_images,
    workspace_tmp_path,
    monkeypatch,
    record_testsuite_property,
    direction,
    phase,
    error_name,
):
    path, cfg, operation, destination, before, target = _case(
        migration_images, workspace_tmp_path, direction
    )
    error_class = {
        "RuntimeError": RuntimeError,
        "KeyboardInterrupt": KeyboardInterrupt,
        "SystemExit": SystemExit,
        "IntegrityError": sqlite3.IntegrityError,
        "OperationalError": sqlite3.OperationalError,
    }[error_name]
    progress = {"copy": False, "rows": False, "revision": False, "injected": 0}
    physical = []
    closed = []

    def fail():
        progress["injected"] += 1
        raise error_class("synthetic migration boundary failure")

    def sql_fault(conn, cursor, statement, parameters, context, executemany):
        point = None
        if statement.startswith("CREATE TEMP TABLE _0009_identifier_history"):
            progress["copy"] = True
            point = "before_copy"
        elif statement == f"DROP TABLE {TABLE}":
            point = "after_copy"
        elif statement.startswith(f"CREATE TABLE {TABLE}"):
            point = "after_drop"
        elif statement.startswith(f"INSERT INTO {TABLE} SELECT"):
            progress["rows"] = True
            point = "after_create"
        elif statement.startswith("CREATE INDEX") and progress["rows"]:
            point = "after_rows"
        elif statement.startswith(f"SELECT * FROM {TABLE} EXCEPT"):
            point = "after_restore"
        elif statement == "PRAGMA foreign_key_check" and progress["rows"]:
            point = "final_check"
        elif statement.startswith("UPDATE alembic_version"):
            progress["revision"] = True
        elif statement == "PRAGMA foreign_keys=ON" and progress["revision"]:
            point = "fk_cleanup"
        if point == phase and progress["injected"] == 0:
            fail()
        if phase == "rollback_cleanup" and point == "after_drop":
            raise RuntimeError("synthetic failure followed by rollback failure")

    def commit_fault(conn):
        if phase == "before_commit" and progress["revision"] and not progress["injected"]:
            assert conn.connection.driver_connection.in_transaction
            fail()

    def observe_close(db, record):
        closed.append(db)
        physical.append(
            {
                "snapshot": _snapshot(db),
                "foreign_keys": db.execute("PRAGMA foreign_keys").fetchone()[0],
                "native_transaction": db.in_transaction,
            }
        )

    # Inject at the real dialect commit/rollback calls, including a lost reply
    # after an actual SQLite commit; product transaction code is not replaced.
    from sqlalchemy.dialects.sqlite.pysqlite import SQLiteDialect_pysqlite

    original_commit = SQLiteDialect_pysqlite.do_commit
    original_rollback = SQLiteDialect_pysqlite.do_rollback

    def commit_reply(dialect, db):
        original_commit(dialect, db)
        if progress["revision"] and not progress["injected"]:
            fail()

    def rollback_failure(dialect, db):
        if progress["copy"] and not progress["injected"]:
            fail()
        original_rollback(dialect, db)

    event.listen(Engine, "before_cursor_execute", sql_fault)
    event.listen(Engine, "commit", commit_fault)
    event.listen(Pool, "close", observe_close)
    try:
        with monkeypatch.context() as patch:
            if phase == "commit_acknowledgment":
                patch.setattr(SQLiteDialect_pysqlite, "do_commit", commit_reply)
            if phase == "rollback_cleanup":
                patch.setattr(SQLiteDialect_pysqlite, "do_rollback", rollback_failure)
            with pytest.raises(BaseException) as raised:
                operation(cfg, destination)
    finally:
        event.remove(Engine, "before_cursor_execute", sql_fault)
        event.remove(Engine, "commit", commit_fault)
        event.remove(Pool, "close", observe_close)
    assert progress["injected"] == 1
    assert isinstance(getattr(raised.value, "orig", raised.value), error_class)
    assert closed
    for db in closed:
        with pytest.raises(sqlite3.ProgrammingError):
            db.execute("SELECT 1")
    after = _reopened(path)
    expected = target if phase in {"fk_cleanup", "commit_acknowledgment"} else before
    assert after == expected
    assert after["temp"] == []
    operation(cfg, destination)
    retried = _reopened(path)
    assert retried == target
    _record(
        record_testsuite_property,
        f"{direction}_{phase}_{error_name}",
        {
            "before": before,
            "target": target,
            "same_physical_before_discard": physical,
            "all_observed_connections_discarded": True,
            "after_reopen": after,
            "retry": retried,
            "reported_failure": type(raised.value).__name__,
            "success_not_reported": True,
        },
    )


@pytest.mark.parametrize("direction", ["upgrade", "downgrade"])
def test_real_revision_abort_and_retry(
    migration_images,
    workspace_tmp_path,
    record_testsuite_property,
    direction,
):
    path, cfg, operation, destination, before, target = _case(
        migration_images, workspace_tmp_path, direction
    )
    with closing(sqlite3.connect(path)) as db, db:
        db.execute(
            "CREATE TRIGGER atomic_revision_fault BEFORE UPDATE ON alembic_version "
            "BEGIN SELECT RAISE(ABORT,'synthetic revision failure'); END"
        )
    with_fault = _reopened(path)
    from sqlalchemy.exc import IntegrityError

    with _observe_disposal() as physical:
        with pytest.raises(IntegrityError, match="synthetic revision failure"):
            operation(cfg, destination)
    assert all(item["snapshot"] == with_fault for item in physical)
    after = _reopened(path)
    assert after == with_fault
    with closing(sqlite3.connect(path)) as db, db:
        db.execute("DROP TRIGGER atomic_revision_fault")
    assert _reopened(path) == before
    operation(cfg, destination)
    assert _reopened(path) == target
    _record(
        record_testsuite_property,
        f"{direction}_revision_abort",
        {
            "before": with_fault,
            "same_physical_before_discard": physical,
            "all_observed_connections_discarded": True,
            "after_reopen": after,
            "retry": target,
        },
    )
