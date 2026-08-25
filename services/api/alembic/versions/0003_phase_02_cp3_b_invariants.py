"""Enforce CP3-B source-chain and verified-mapping invariants.

Revision ID: 0003_phase_02_cp3_b_invariants
Revises: 0002_phase_02_cp3_foundation
"""

from collections import defaultdict
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.engine import Connection

revision: str = "0003_phase_02_cp3_b_invariants"
down_revision: str | None = "0002_phase_02_cp3_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_INDEXES = (
    (
        "uq_provider_source_versions_original_root",
        "provider_source_versions",
        ["canonical_request_id"],
        sa.text("revision_status = 'ORIGINAL'"),
    ),
    (
        "uq_provider_source_versions_supersedes",
        "provider_source_versions",
        ["supersedes_id"],
        sa.text("supersedes_id IS NOT NULL"),
    ),
    (
        "uq_provider_identity_mappings_current_verified",
        "provider_identity_mappings",
        ["provider_security_identity_id"],
        sa.text("mapping_status = 'VERIFIED' AND valid_to IS NULL"),
    ),
)


def _validate_existing_source_chains(connection: Connection) -> None:
    rows = connection.execute(
        sa.text(
            "SELECT source_version_id, canonical_request_id, revision_status, supersedes_id "
            "FROM provider_source_versions"
        )
    ).mappings()
    histories: dict[str, dict[str, tuple[str, str | None]]] = defaultdict(dict)
    for row in rows:
        histories[str(row["canonical_request_id"])][str(row["source_version_id"])] = (
            str(row["revision_status"]),
            None if row["supersedes_id"] is None else str(row["supersedes_id"]),
        )

    for nodes in histories.values():
        roots = [
            source_id
            for source_id, (status, parent_id) in nodes.items()
            if status == "ORIGINAL" and parent_id is None
        ]
        if len(roots) != 1:
            raise RuntimeError("provider source history must have exactly one original root")

        children: dict[str, list[str]] = defaultdict(list)
        for source_id, (status, parent_id) in nodes.items():
            if status == "ORIGINAL":
                if parent_id is not None:
                    raise RuntimeError("provider source original cannot supersede another version")
                continue
            if parent_id is None or parent_id not in nodes:
                raise RuntimeError(
                    "provider source revision must supersede its request-local parent"
                )
            children[parent_id].append(source_id)
            if len(children[parent_id]) > 1:
                raise RuntimeError("provider source history contains a revision fork")

        visited: set[str] = set()
        current = roots[0]
        while True:
            if current in visited:
                raise RuntimeError("provider source history contains a revision cycle")
            visited.add(current)
            next_versions = children.get(current, [])
            if not next_versions:
                break
            current = next_versions[0]
        if len(visited) != len(nodes):
            raise RuntimeError("provider source history is not one linear chain")


def _interval_start(value: object) -> str:
    return "0001-01-01" if value is None else str(value)


def _interval_end(value: object) -> str:
    return "9999-12-31" if value is None else str(value)


def _validate_existing_verified_mapping_intervals(connection: Connection) -> None:
    rows = connection.execute(
        sa.text(
            "SELECT mapping_id, provider_security_identity_id, valid_from, valid_to "
            "FROM provider_identity_mappings "
            "WHERE mapping_status = 'VERIFIED'"
        )
    ).mappings()
    mappings: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    for row in rows:
        mappings[str(row["provider_security_identity_id"])].append(
            (
                str(row["mapping_id"]),
                _interval_start(row["valid_from"]),
                _interval_end(row["valid_to"]),
            )
        )

    for intervals in mappings.values():
        for index, (_, left_start, left_end) in enumerate(intervals):
            for _, right_start, right_end in intervals[index + 1 :]:
                if left_start <= right_end and right_start <= left_end:
                    raise RuntimeError("verified provider identity mapping intervals overlap")


def _validate_existing_data(connection: Connection) -> None:
    _validate_existing_source_chains(connection)
    _validate_existing_verified_mapping_intervals(connection)


def upgrade() -> None:
    _validate_existing_data(op.get_bind())
    created: list[tuple[str, str]] = []
    try:
        for name, table_name, columns, where_clause in _INDEXES:
            op.create_index(
                name,
                table_name,
                columns,
                unique=True,
                sqlite_where=where_clause,
            )
            created.append((name, table_name))
    except Exception:
        cleanup_failure: Exception | None = None
        for name, table_name in reversed(created):
            try:
                op.drop_index(name, table_name=table_name)
            except Exception as exc:
                cleanup_failure = exc
                break
        if cleanup_failure is not None:
            raise RuntimeError(
                "CP3-B invariant migration cleanup failed closed"
            ) from cleanup_failure
        raise


def downgrade() -> None:
    for name, table_name, _, _ in reversed(_INDEXES):
        op.drop_index(name, table_name=table_name)
