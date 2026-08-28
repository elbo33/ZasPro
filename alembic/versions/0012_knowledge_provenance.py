"""knowledge item provenance (M4)

Revision ID: 0012_knowledge_provenance
Revises: 0011_knowledge_review_and_export
Create Date: 2026-08-28 15:30:00.000000

Every knowledge item now carries `provenance` (EXAM_TASK / MARKING_SCHEME /
DISTRACTOR / INFORMATOR / AGENT_KNOWLEDGE) — the agent produces a complete spec
for every topic, from its own subject knowledge where no exam material exists,
and this records which (ADR 0011 §2). Replaces `misconceptions.source_kind`,
which was misconception-only and framed provenance as a gate.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012_knowledge_provenance"
down_revision: str | Sequence[str] | None = "0011_knowledge_review_and_export"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLES = (
    "concepts", "formulas", "methods", "examples", "misconceptions",
    "learning_objectives",
)


def upgrade() -> None:
    for t in _TABLES:
        op.add_column(t, sa.Column(
            "provenance", sa.String(length=32), nullable=False,
            server_default="AGENT_KNOWLEDGE",
        ))
    op.drop_column("misconceptions", "source_kind")


def downgrade() -> None:
    op.add_column("misconceptions", sa.Column(
        "source_kind", sa.String(length=32), nullable=False,
        server_default="AGENT_INFERENCE",
    ))
    for t in reversed(_TABLES):
        op.drop_column(t, "provenance")
