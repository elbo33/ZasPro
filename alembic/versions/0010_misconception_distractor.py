"""misconceptions.distractor (M4)

Revision ID: 0010_misconception_distractor
Revises: 0009_knowledge_tables
Create Date: 2026-08-28 12:00:00.000000

Adds the `distractor` column for `source_kind = DISTRACTOR_INFERENCE`: the
specific multiple-choice distractor a misconception was read off. Also widens
`misconceptions.source_kind` from VARCHAR(15) to VARCHAR(32): the non-native
enum column is sized to the longest member, and "DISTRACTOR_INFERENCE" (20) no
longer fits. 32 leaves headroom so a longer member later needs no migration.
There is no CHECK constraint to touch.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_misconception_distractor"
down_revision: str | Sequence[str] | None = "0009_knowledge_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "misconceptions", sa.Column("distractor", sa.String(length=255), nullable=True)
    )
    op.alter_column(
        "misconceptions", "source_kind",
        existing_type=sa.String(length=15), type_=sa.String(length=32),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "misconceptions", "source_kind",
        existing_type=sa.String(length=32), type_=sa.String(length=15),
        existing_nullable=False,
    )
    op.drop_column("misconceptions", "distractor")
