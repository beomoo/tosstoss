"""0009 reconstruction preserves historical rows and relational/immutability guards."""

from types import SimpleNamespace

import pytest
from alembic import command
from sqlalchemy.exc import IntegrityError
from tests.backend.conftest import FIXTURE_DIR, alembic_config
from tests.backend.security_authority_test_support import (
    approved_issuer,
    authorization,
    business,
    candidate,
    insert,
)
from tests.backend.test_security_authority_decision_engine import _us_evaluation
from tests.backend.test_security_authority_remediation import reseal

from toss_dashboard_api.contracts import security_authority as c
from toss_dashboard_api.fixtures.importer import FixtureImporter
from toss_dashboard_api.repositories.fixture import FixtureRepository
from toss_dashboard_api.storage.database import create_database_engine, session_factory

PREVIOUS = "0008_phase_02_cp3_c2_c_security_authority"
REVISION = "0009_phase_02_cp3_c2_c3_identifier_claim_contract"


def snapshot(connection):
    tables = [
        row[0]
        for row in connection.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name!='alembic_version' ORDER BY name"
        )
    ]
    return {
        table: connection.exec_driver_sql(f'SELECT * FROM "{table}" ORDER BY rowid').all()
        for table in tables
    }


def schema(connection):
    return connection.exec_driver_sql(
        "SELECT type, name, tbl_name, sql FROM sqlite_master ORDER BY name"
    ).all()


def test_populated_upgrade_and_v01_only_downgrade_preserve_exact_rows_and_shape(workspace_tmp_path):
    url = f"sqlite:///{workspace_tmp_path / 'identifier_contract.sqlite3'}"
    cfg = alembic_config(url)
    command.upgrade(cfg, PREVIOUS)
    engine = create_database_engine(url)
    try:
        FixtureImporter(session_factory(engine)).import_repository(FixtureRepository(FIXTURE_DIR))
        issuer = approved_issuer(SimpleNamespace(engine=engine))
        with engine.begin() as connection:
            graph = candidate(connection, issuer)
            # Frozen v0.1's broad read contract also allowed this pair. Preserve
            # even such history verbatim, but never accept it as new US proof.
            legacy = reseal(
                graph["identifier"],
                claim_id="historical_v01_registered",
                identifier_kind="SEC_REGISTERED_CLASS",
            )
            insert(connection, legacy)
            auth = authorization(connection, issuer, graph, "history")
            business(connection, graph, auth, "history")
            old = snapshot(connection)
            old_schema = schema(connection)
            old_fks = connection.exec_driver_sql(
                "PRAGMA foreign_key_list(security_identifier_claims)"
            ).all()
            payload = graph["identifier"].model_dump_json()
            assert c.IdentifierClaim.model_validate_json(payload) == graph["identifier"]
            assert c.IdentifierClaim.model_validate_json(legacy.model_dump_json()) == legacy
        command.upgrade(cfg, REVISION)
        with engine.begin() as connection:
            assert snapshot(connection) == old
            assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []
            assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
            assert (
                connection.exec_driver_sql(
                    "PRAGMA foreign_key_list(security_identifier_claims)"
                ).all()
                == old_fks
            )
            upgraded_schema = schema(connection)
            changed_objects = {row[1] for row in set(old_schema) ^ set(upgraded_schema)}
            assert changed_objects == {
                "security_identifier_claims",
                "trg_0009_identifier_provenance_owner",
            }
            for sql in (
                "UPDATE security_identifier_claims SET identifier_value=identifier_value",
                "DELETE FROM security_identifier_claims",
            ):
                with pytest.raises(IntegrityError, match="trg_0008_"):
                    with connection.begin_nested():
                        connection.exec_driver_sql(sql)
            for changes in (
                {},
                {"claim_id": "wrong_hash", "application_hash": c.security_hash("x")},
            ):
                with pytest.raises(IntegrityError):
                    with connection.begin_nested():
                        insert(connection, graph["identifier"], **changes)
            with pytest.raises(IntegrityError, match="trg_0009_identifier_provenance_owner"):
                with connection.begin_nested():
                    insert(connection, legacy, claim_id="new_v01_registered_forbidden")
        command.upgrade(cfg, REVISION)
        with engine.connect() as connection:
            assert schema(connection) == upgraded_schema
        command.downgrade(cfg, PREVIOUS)
        with engine.connect() as connection:
            assert snapshot(connection) == old
            assert schema(connection) == old_schema
            assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []
        command.upgrade(cfg, REVISION)
        with engine.connect() as connection:
            assert snapshot(connection) == old
            assert schema(connection) == upgraded_schema
    finally:
        engine.dispose()


def test_v02_history_refuses_downgrade_without_any_change(database_context):
    _, _, result = _us_evaluation(database_context)
    assert result.identifier_claims[0].contract_version == "security-identifier-claim/0.2.0"
    with database_context.engine.connect() as connection:
        before = snapshot(connection), schema(connection)
    with pytest.raises(RuntimeError, match="downgrade refused: v0.2 identifier history exists"):
        command.downgrade(alembic_config(database_context.url), PREVIOUS)
    with database_context.engine.connect() as connection:
        assert (snapshot(connection), schema(connection)) == before
        assert (
            connection.exec_driver_sql("SELECT version_num FROM alembic_version").scalar_one()
            == REVISION
        )
        assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []


def test_0009_fresh_upgrade_downgrade_reupgrade(workspace_tmp_path):
    url = f"sqlite:///{workspace_tmp_path / 'fresh.sqlite3'}"
    cfg = alembic_config(url)
    command.upgrade(cfg, REVISION)
    command.downgrade(cfg, "base")
    command.upgrade(cfg, REVISION)
    engine = create_database_engine(url)
    try:
        with engine.connect() as connection:
            assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
            assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []
    finally:
        engine.dispose()


def test_failed_reconstruction_rolls_back_all_history_and_schema(workspace_tmp_path, monkeypatch):
    from sqlalchemy.engine import Connection

    url = f"sqlite:///{workspace_tmp_path / 'rollback.sqlite3'}"
    cfg = alembic_config(url)
    command.upgrade(cfg, PREVIOUS)
    engine = create_database_engine(url)
    try:
        FixtureImporter(session_factory(engine)).import_repository(FixtureRepository(FIXTURE_DIR))
        issuer = approved_issuer(SimpleNamespace(engine=engine))
        with engine.begin() as connection:
            candidate(connection, issuer)
            before = snapshot(connection), schema(connection)
            connection.exec_driver_sql(
                "CREATE INDEX unexpected_identifier_index ON security_identifier_claims(scope)"
            )
            extra_schema = schema(connection)
        with pytest.raises(RuntimeError, match="identifier predecessor schema mismatch"):
            command.upgrade(cfg, REVISION)
        with engine.begin() as connection:
            assert snapshot(connection) == before[0]
            assert schema(connection) == extra_schema
            connection.exec_driver_sql("DROP INDEX unexpected_identifier_index")
        execute = Connection.exec_driver_sql

        def fail_after_rebuild(connection, sql, *args, **kwargs):
            if sql.startswith("CREATE TRIGGER trg_0009_identifier_provenance_owner"):
                raise RuntimeError("synthetic post-copy migration failure")
            return execute(connection, sql, *args, **kwargs)

        with monkeypatch.context() as patch:
            patch.setattr(Connection, "exec_driver_sql", fail_after_rebuild)
            with pytest.raises(RuntimeError, match="synthetic post-copy migration failure"):
                command.upgrade(cfg, REVISION)
        with engine.connect() as connection:
            assert (snapshot(connection), schema(connection)) == before
            assert (
                connection.exec_driver_sql("SELECT version_num FROM alembic_version").scalar_one()
                == PREVIOUS
            )
            assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []
            assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
        command.upgrade(cfg, REVISION)
    finally:
        engine.dispose()
