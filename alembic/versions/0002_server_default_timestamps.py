"""server_default timestamps for created/recorded_at columns

Revision ID: 0002_server_default_timestamps
Revises: 0001_initial_schema
Create Date: 2026-05-10

Adds ``server_default=func.now()`` (CURRENT_TIMESTAMP under SQLite) to the
ORM-managed timestamp columns so concurrent inserts and raw-SQL paths get a
DB-side default. Closes debt D6.

Affected columns:

  - runs.started_at
  - metrics.computed_at
  - emissions.recorded_at

Uses ``batch_alter_table`` because SQLite does not support ``ALTER COLUMN``
directly; Alembic's batch mode rewrites the table to apply the change.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_server_default_timestamps"
down_revision: str | Sequence[str] | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_TARGETS = (
    ("runs", "started_at", False),
    ("metrics", "computed_at", False),
    ("emissions", "recorded_at", False),
)


def upgrade() -> None:
    for table, col, nullable in _TARGETS:
        with op.batch_alter_table(table, recreate="always") as batch:
            batch.alter_column(
                col,
                existing_type=sa.DateTime(timezone=True),
                existing_nullable=nullable,
                server_default=sa.func.now(),
            )


def downgrade() -> None:
    for table, col, nullable in _TARGETS:
        with op.batch_alter_table(table, recreate="always") as batch:
            batch.alter_column(
                col,
                existing_type=sa.DateTime(timezone=True),
                existing_nullable=nullable,
                server_default=None,
            )
