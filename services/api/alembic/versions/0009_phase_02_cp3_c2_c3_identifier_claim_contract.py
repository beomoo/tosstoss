"""ADR-021 versioned identifier provenance; preserve the frozen 0008 ledger."""

from pathlib import Path
from runpy import run_path

from alembic import op

revision = "0009_phase_02_cp3_c2_c3_identifier_claim_contract"
down_revision = "0008_phase_02_cp3_c2_c_security_authority"
branch_labels = None
depends_on = None

# Reuse the exact accepted DDL, including every FK/UNIQUE/check and immutable guard.
_BASE = run_path(str(Path(__file__).with_name(f"{down_revision}.py")))
_TABLE = "security_identifier_claims"
_TEMP = "_0009_identifier_history"
_OLD_DDL = dict(_BASE["_TABLE_DDL"])[_TABLE]
_NEW_DDL = _OLD_DDL.replace(
    "CHECK (scope IN ('SECURITY_IDENTIFIER'))",
    "CHECK (scope IN ('SECURITY_IDENTIFIER', 'IDENTIFIER_PROVENANCE'))",
).replace(
    "CHECK (contract_version IN ('security-identifier-claim/0.1.0'))",
    """CHECK (
        (contract_version='security-identifier-claim/0.1.0'
         AND scope='SECURITY_IDENTIFIER')
        OR (contract_version='security-identifier-claim/0.2.0' AND (
            (identifier_kind='KRX_ISIN' AND scope='SECURITY_IDENTIFIER')
            OR (identifier_kind='SEC_REGISTERED_CLASS' AND scope='IDENTIFIER_PROVENANCE')
        ))
    )""",
)
_INDEXES = tuple((name, sql) for name, sql in _BASE["_INDEX_DDL"] if f" ON {_TABLE} (" in sql)
_IMMUTABILITY = tuple((name, sql) for name, sql in _BASE["_TRIGGER_DDL"] if f" ON {_TABLE} " in sql)
_GUARD = "trg_0009_identifier_provenance_owner"
_GUARD_DDL = f"""CREATE TRIGGER {_GUARD} BEFORE INSERT ON {_TABLE}
WHEN NEW.identifier_kind='SEC_REGISTERED_CLASS'
 AND (NEW.contract_version!='security-identifier-claim/0.2.0' OR NOT EXISTS (
    SELECT 1 FROM security_authority_evidence_applications a
    WHERE a.application_id=NEW.application_id AND a.content_hash=NEW.application_hash
      AND a.provider_id=NEW.provider_id AND a.issuer_id=NEW.issuer_id
      AND a.security_id=NEW.security_id AND a.scope='IDENTIFIER_PROVENANCE'
      AND a.status='ADMITTED' AND a.requested_weight=3
      AND a.source_namespace='SEC_ACCEPTED_8A' AND a.document_kind='SEC_FORM_8A'
      AND a.subject_role='SEC_REGISTRANT' AND a.fixture_taint=0 AND a.test_taint=0
 ))
BEGIN SELECT RAISE(ABORT, '{_GUARD}'); END"""


def _rebuild(*, forward: bool) -> None:
    connection = op.get_bind()
    expected = _OLD_DDL if forward else _NEW_DDL
    target = _NEW_DDL if forward else _OLD_DDL
    if connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() != 1:
        raise RuntimeError("0009 requires foreign_keys ON")
    objects = dict(connection.exec_driver_sql("SELECT name, sql FROM sqlite_master").all())
    required = ((_TABLE, expected), *_INDEXES, *_IMMUTABILITY)
    if not forward:
        required += ((_GUARD, _GUARD_DDL),)
    owned = {
        row[0]
        for row in connection.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE tbl_name=? AND sql IS NOT NULL", (_TABLE,)
        )
    }
    if owned != {name for name, _ in required} or any(
        objects.get(name) != sql for name, sql in required
    ):
        raise RuntimeError("0009 identifier predecessor schema mismatch")
    if forward and _GUARD in objects:
        raise RuntimeError("0009 pre-existing guard collision")
    if connection.exec_driver_sql("PRAGMA foreign_key_check").first() is not None:
        raise RuntimeError("0009 predecessor foreign-key check failed")
    if (
        not forward
        and connection.exec_driver_sql(
            f"SELECT 1 FROM {_TABLE} WHERE contract_version!='security-identifier-claim/0.1.0'"
            " LIMIT 1"
        ).first()
        is not None
    ):
        raise RuntimeError("0009 downgrade refused: v0.2 identifier history exists")

    # SQLite cannot replace a referenced parent with FK enforcement enabled. The
    # change is a single explicit transaction, checked before commit; FK is
    # restored even on rollback. No accepted rows or payloads are resealed.
    with op.get_context().autocommit_block():
        connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
        try:
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            connection.exec_driver_sql(f"CREATE TEMP TABLE {_TEMP} AS SELECT * FROM {_TABLE}")
            connection.exec_driver_sql(f"DROP TABLE {_TABLE}")
            connection.exec_driver_sql(target)
            connection.exec_driver_sql(f"INSERT INTO {_TABLE} SELECT * FROM {_TEMP}")
            for _, sql in (*_INDEXES, *_IMMUTABILITY):
                connection.exec_driver_sql(sql)
            if forward:
                connection.exec_driver_sql(_GUARD_DDL)
            for left, right in ((_TABLE, _TEMP), (_TEMP, _TABLE)):
                if (
                    connection.exec_driver_sql(
                        f"SELECT * FROM {left} EXCEPT SELECT * FROM {right}"
                    ).first()
                    is not None
                ):
                    raise RuntimeError("0009 identifier history preservation failed")
            if connection.exec_driver_sql("PRAGMA foreign_key_check").first() is not None:
                raise RuntimeError("0009 reconstructed foreign-key check failed")
            connection.exec_driver_sql(f"DROP TABLE {_TEMP}")
            connection.exec_driver_sql("COMMIT")
        except Exception:
            connection.exec_driver_sql("ROLLBACK")
            raise
        finally:
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
            if connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() != 1:
                raise RuntimeError("0009 could not restore foreign_keys ON")


def upgrade() -> None:
    _rebuild(forward=True)


def downgrade() -> None:
    _rebuild(forward=False)
