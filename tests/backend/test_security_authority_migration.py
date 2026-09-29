from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from alembic import command
from sqlalchemy.exc import IntegrityError
from tests.backend.conftest import FIXTURE_DIR, alembic_config
from tests.backend.security_authority_test_support import (
    HASH,
    TABLES,
    approved_issuer,
    authorization,
    business,
    candidate,
    head,
    insert,
    policy,
)

from toss_dashboard_api.contracts import security_authority as c
from toss_dashboard_api.fixtures.importer import FixtureImporter
from toss_dashboard_api.repositories.fixture import FixtureRepository
from toss_dashboard_api.storage.database import create_database_engine, session_factory

REVISION = "0008_phase_02_cp3_c2_c_security_authority"
PREVIOUS = "0007_phase_02_cp3_c2_b2_c_counter_capability_bootstrap"


@pytest.fixture
def graph(database_context):
    issuer = approved_issuer(database_context)
    with database_context.engine.begin() as connection:
        values = candidate(connection, issuer)
    return database_context, issuer, values


def test_migration_fresh_repeat_downgrade_reupgrade_and_old_data(workspace_tmp_path: Path) -> None:
    url = f"sqlite:///{workspace_tmp_path / '0008.sqlite3'}"
    cfg = alembic_config(url)
    command.upgrade(cfg, PREVIOUS)
    engine = create_database_engine(url)
    FixtureImporter(session_factory(engine)).import_repository(FixtureRepository(FIXTURE_DIR))
    approved_issuer(SimpleNamespace(engine=engine))
    with engine.connect() as connection:
        original = {
            r[0]
            for r in connection.exec_driver_sql("SELECT name FROM sqlite_master WHERE type='table'")
        }
        before = {
            t: connection.exec_driver_sql(f"SELECT * FROM {t}").all()
            for t in original
            if t != "alembic_version"
        }
        assert sum(len(rows) for rows in before.values()) > 0
    command.upgrade(cfg, REVISION)
    with engine.connect() as connection:
        assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
        actual = {
            r[0]
            for r in connection.exec_driver_sql("SELECT name FROM sqlite_master WHERE type='table'")
        }
        assert actual - original == set(TABLES.values())
        assert {t: connection.exec_driver_sql(f"SELECT * FROM {t}").all() for t in before} == before
        first = connection.exec_driver_sql(
            "SELECT type,name,sql FROM sqlite_master ORDER BY name"
        ).all()
        assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []
    command.upgrade(cfg, REVISION)
    with engine.connect() as connection:
        assert (
            connection.exec_driver_sql(
                "SELECT type,name,sql FROM sqlite_master ORDER BY name"
            ).all()
            == first
        )
    command.downgrade(cfg, PREVIOUS)
    with engine.connect() as connection:
        assert {t: connection.exec_driver_sql(f"SELECT * FROM {t}").all() for t in before} == before
        assert {
            r[0]
            for r in connection.exec_driver_sql("SELECT name FROM sqlite_master WHERE type='table'")
        } == original
    command.upgrade(cfg, REVISION)
    with engine.connect() as connection:
        assert (
            connection.exec_driver_sql(
                "SELECT type,name,sql FROM sqlite_master ORDER BY name"
            ).all()
            == first
        )
    engine.dispose()


def test_nonempty_downgrade_preserves_history(database_context) -> None:
    with database_context.engine.begin() as connection:
        insert(connection, policy())
    with pytest.raises(RuntimeError, match="not empty"):
        command.downgrade(alembic_config(database_context.url), PREVIOUS)
    with database_context.engine.connect() as connection:
        assert (
            connection.exec_driver_sql("SELECT version_num FROM alembic_version").scalar_one()
            == REVISION
        )
        assert (
            connection.exec_driver_sql(
                "SELECT count(*) FROM security_authority_source_policies"
            ).scalar_one()
            == 1
        )


def test_m1_authentication_without_approval_or_link(database_context) -> None:
    context = database_context
    issuer = approved_issuer(context)
    with context.engine.begin() as connection:
        g = candidate(connection, issuer, persist_subjects=False)
        auth = authorization(connection, issuer, g, "standalone")
        savepoint = connection.begin_nested()
        insert(connection, g["subject"])
        insert(connection, g["profile"])
        business(connection, g, auth, "rolled_back")
        savepoint.rollback()
        assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []
    with context.engine.begin() as connection:
        for table in ("canonical_security_subjects", "security_authority_profiles"):
            assert connection.exec_driver_sql(f"SELECT count(*) FROM {table}").scalar_one() == 0
        assert (
            connection.exec_driver_sql(
                "SELECT count(*) FROM security_reviewer_authentication_events"
            ).scalar_one()
            == 1
        )
        assert (
            connection.exec_driver_sql("SELECT count(*) FROM security_approval_events").scalar_one()
            == 0
        )
        assert (
            connection.exec_driver_sql("SELECT count(*) FROM security_authority_links").scalar_one()
            == 0
        )
        with pytest.raises(IntegrityError):
            with connection.begin_nested():
                insert(connection, auth["consumption"], consumption_id="consumption_replay")


def test_exact_approval_head_and_one_auth_one_disposition(graph) -> None:
    context, issuer, g = graph
    with context.engine.begin() as connection:
        auth = authorization(connection, issuer, g, "initial")
        rows = business(connection, g, auth, "initial")
        h = head(connection, g, rows, persist=False)
        with pytest.raises(IntegrityError, match="FOREIGN KEY constraint"):
            with connection.begin_nested():
                insert(connection, h, security_id="security_wrong_subject")
        insert(connection, h)
        assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []
        with pytest.raises(IntegrityError):
            with connection.begin_nested():
                insert(connection, rows["event"], approval_event_id="event_duplicate")
        with pytest.raises(IntegrityError):
            with connection.begin_nested():
                connection.exec_driver_sql(
                    "UPDATE security_authority_link_heads SET security_id=?",
                    (
                        c.security_id_for_anchor(
                            c.kr_anchor(issuer["link"]["issuer_id"], "KR7000660001")
                        ),
                    ),
                )
        with pytest.raises(IntegrityError):
            with connection.begin_nested():
                connection.exec_driver_sql(
                    "UPDATE issuer_authority_link_heads SET state_hash=?", ("sha256:" + "f" * 64,)
                )
        assert h.link_id == rows["link"].link_id


@pytest.mark.parametrize(
    "kind,field,value",
    [
        (c.SourcePolicy, "production_eligible", 1),
        (c.EvidenceApplication, "requested_weight", 3),
        (c.EvidenceApplication, "policy_hash", HASH),
        (c.BundleApplication, "application_hash", HASH),
        (c.Bundle, "issuer_link_hash", HASH),
        (c.Bundle, "issuer_link_state", "REVOKED"),
        (c.Decision, "bundle_hash", HASH),
    ],
)
def test_relational_binding_rejects_corrupt_rows(graph, kind, field, value) -> None:
    context, issuer, g = graph
    source = next(v for v in g.values() if type(v) is kind)
    with context.engine.begin() as connection:
        # First prove the otherwise-identical new row is legal. No duplicate PK can mask the FK.
        if kind is c.SourcePolicy:
            changes = dict(policy_id="policy_clone", policy_version="test-clone")
        elif kind is c.EvidenceApplication:
            changes = dict(application_id="application_clone")
        elif kind is c.Bundle:
            changes = dict(bundle_id="bundle_clone")
        elif kind is c.Decision:
            changes = dict(decision_id="decision_clone", supersedes_decision_id=source.decision_id)
        else:
            insert(connection, g["bundle"], bundle_id="bundle_clone")
            changes = dict(bundle_id="bundle_clone")
        positive = connection.begin_nested()
        insert(connection, source, **changes)
        positive.rollback()
        with pytest.raises(
            IntegrityError, match="CHECK constraint|FOREIGN KEY constraint|trg_0008_"
        ):
            with connection.begin_nested():
                insert(connection, source, **(changes | {field: value}))


def test_append_only_update_delete_for_all_populated_graph_history(graph) -> None:
    context, issuer, g = graph
    with context.engine.begin() as connection:
        auth = authorization(connection, issuer, g, "immutable")
        rows = business(connection, g, auth, "immutable")
        head(connection, g, rows)
        populated = []
        for table in TABLES.values():
            if table == "security_authority_link_heads":
                continue
            if connection.exec_driver_sql(f"SELECT count(*) FROM {table}").scalar_one():
                populated.append(table)
                for sql in (
                    f"UPDATE {table} SET payload_json=payload_json",
                    f"DELETE FROM {table}",
                ):
                    with pytest.raises(IntegrityError, match="trg_0008_"):
                        with connection.begin_nested():
                            connection.exec_driver_sql(sql)
        assert len(populated) >= 17
        with pytest.raises(IntegrityError):
            with connection.begin_nested():
                connection.exec_driver_sql("DELETE FROM security_authority_link_heads")


def test_all_23_tables_have_required_immutable_triggers(database_context) -> None:
    with database_context.engine.connect() as connection:
        triggers = connection.exec_driver_sql(
            "SELECT tbl_name,sql FROM sqlite_master WHERE type='trigger'"
        ).all()
        for table in TABLES.values():
            for operation in (
                ("DELETE",) if table == "security_authority_link_heads" else ("UPDATE", "DELETE")
            ):
                assert any(
                    t == table and f"BEFORE {operation} ON {table} WHEN 1" in sql
                    for t, sql in triggers
                )
