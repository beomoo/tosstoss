"""Add Security successes to the frozen R1 connected counter union."""

import hashlib
import json
from pathlib import Path
from runpy import run_path

from alembic import op

from toss_dashboard_api.reviewer.ledger import Ledger

revision = "0010_phase_02_cp3_c3_shared_counter_union"
down_revision = "0009_phase_02_cp3_c2_c3_identifier_claim_contract"
branch_labels = None
depends_on = None

_BASE = run_path(
    str(Path(__file__).with_name("0007_phase_02_cp3_c2_b2_c_counter_capability_bootstrap.py"))
)
_OLD = (*_BASE["_COUNTER_GUARD_DDL"], _BASE["_ASSERTION_COUNTER_GUARD_DDL"])
_SECURITY = "trg_security_reviewer_authentication_events_counter_union_guard"
# Exact sqlite_master type/name/table/SQL inventory after real 0001 -> 0009,
# restricted to all reviewer_* and security_* objects (305 objects). This also
# verifies CHECK/FK/UNIQUE/immutability and rejects extra conflicting guards.
_PREDECESSOR_SCHEMA_SHA256 = "".join(
    (
        "82ed7cde",
        "7ac58f09",
        "10b62d3f",
        "ade05b76",
        "94625f5b",
        "e08a700a",
        "ff450273",
        "ddc77c77",
    )
)


def _include_security(sql: str) -> str:
    """Extend EVERY issuer read, keeping all 0007 predicates verbatim.

    UNION ALL preserves duplicates for the frozen fork/duplicate rejection.
    Security's frozen table admits only VERIFIED + SUCCEEDED consumption,
    verified flags and credential bindings; malformed persisted rows are
    rejected by admission before migration and by the runtime reader.
    """
    columns = (
        "webauthn_credential_id, authentication_result, counter_capability, "
        "previous_sign_count, asserted_sign_count"
    )
    return sql.replace(
        "FROM reviewer_authentication_events",
        f"FROM (SELECT {columns} FROM reviewer_authentication_events UNION ALL "
        f"SELECT {columns} FROM security_reviewer_authentication_events)",
    )


_NEW = (
    *((name, _include_security(sql)) for name, sql in _OLD),
    (
        _SECURITY,
        _include_security(
            _BASE["_counter_union_trigger_sql"](
                trigger_name=_SECURITY,
                table_name="security_reviewer_authentication_events",
                credential_column="webauthn_credential_id",
            )
        ),
    ),
)


def _verify_schema(connection, *, forward: bool) -> None:
    expected_revision = down_revision if forward else revision
    if (
        connection.exec_driver_sql("SELECT version_num FROM alembic_version").scalar_one()
        != expected_revision
    ):
        raise RuntimeError("0010 requires exact predecessor revision")
    objects = [
        tuple(row)
        for row in connection.exec_driver_sql(
            "SELECT type,name,tbl_name,sql FROM sqlite_master "
            "WHERE tbl_name GLOB 'reviewer_*' OR tbl_name GLOB 'security_*' ORDER BY type,name"
        )
    ]
    by_name = {row[1]: row[3] for row in objects}
    for name, sql in _OLD if forward else _NEW:
        if by_name.get(name) != sql:
            raise RuntimeError(f"0010 exact counter trigger mismatch: {name}")
    if forward and _SECURITY in by_name:
        raise RuntimeError("0010 refuses pre-existing Security counter guard")
    # Normalize only verified 0010 replacements back to their exact predecessor
    # for the same inventory check in both directions.
    old = dict(_OLD)
    predecessor = [
        (kind, name, table, old.get(name, sql))
        for kind, name, table, sql in objects
        if name != _SECURITY
    ]
    digest = hashlib.sha256(json.dumps(predecessor, separators=(",", ":")).encode()).hexdigest()
    if digest != _PREDECESSOR_SCHEMA_SHA256:
        raise RuntimeError("0010 exact predecessor schema mismatch")


def _replace(*, forward: bool) -> None:
    connection = op.get_bind()
    if connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() != 1:
        raise RuntimeError("0010 requires foreign_keys ON")
    # sqlite3 legacy mode does not BEGIN for DDL. Start the native transaction
    # under the existing Alembic/SQLAlchemy owner, never COMMIT/ROLLBACK here.
    # Alembic's revision UPDATE and env.py's failure invalidation share it.
    if not connection.connection.driver_connection.in_transaction:
        connection.exec_driver_sql("BEGIN IMMEDIATE")
    _verify_schema(connection, forward=forward)
    principals = connection.exec_driver_sql(
        "SELECT os_owner_sid_hash FROM reviewer_principals"
    ).all()
    # The existing R1 algorithm validates registration/bootstrap and every edge,
    # including all historical revoked/replaced credentials and Security input.
    Ledger(connection, principals[0][0] if principals else "")
    if (
        not forward
        and connection.exec_driver_sql(
            "SELECT 1 FROM security_reviewer_authentication_events "
            "WHERE previous_sign_count IS NOT NULL OR asserted_sign_count IS NOT NULL LIMIT 1"
        ).first()
    ):
        raise RuntimeError("0010 downgrade refused: accepted numeric Security history")
    for name, _ in _OLD if forward else _NEW:
        connection.exec_driver_sql(f"DROP TRIGGER {name}")
    for _, sql in _NEW if forward else _OLD:
        connection.exec_driver_sql(sql)


def upgrade() -> None:
    _replace(forward=True)


def downgrade() -> None:
    _replace(forward=False)
