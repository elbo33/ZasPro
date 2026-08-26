"""exercises.own_figure_count

Splits the figure count: `own_figure_count` is the `<w:drawing>` count in the
exercise's own DOCX range (a distinct figure region); `expected_figure_count`
stays as own + inherited-from-parent. Lets the ingestion report show
"N regions expected / N rendered" without conflating it with the count of
figure-bearing exercises (parents + inheriting subtasks).

Revision ID: 0003_exercise_own_figure_count
Revises: 0002_ingestion_exercises_jobs
Create Date: 2026-08-27
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_exercise_own_figure_count"
down_revision: str | Sequence[str] | None = "0002_ingestion_exercises_jobs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "exercises",
        sa.Column("own_figure_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.alter_column("exercises", "own_figure_count", server_default=None)


def downgrade() -> None:
    op.drop_column("exercises", "own_figure_count")
