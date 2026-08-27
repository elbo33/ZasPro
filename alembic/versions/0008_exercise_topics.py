"""exercise_topics (M4 aggregation)

Revision ID: 0008_exercise_topics
Revises: 0007_review_input_defect
Create Date: 2026-08-28 00:45:11.179709

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_exercise_topics"
down_revision: str | Sequence[str] | None = "0007_review_input_defect"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "exercise_topics",
        sa.Column("exercise_id", sa.Integer(), nullable=False),
        sa.Column("topic_id", sa.Integer(), nullable=False),
        sa.Column(
            "role",
            sa.Enum("PRIMARY", "SECONDARY", name="topic_role", native_enum=False),
            nullable=False,
        ),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("source_chunk_mapping_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["exercise_id"], ["exercises.id"],
            name=op.f("fk_exercise_topics_exercise_id_exercises"), ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_chunk_mapping_id"], ["chunk_mappings.id"],
            name=op.f("fk_exercise_topics_source_chunk_mapping_id_chunk_mappings"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["topic_id"], ["topics.id"],
            name=op.f("fk_exercise_topics_topic_id_topics"), ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "exercise_id", "topic_id", name=op.f("pk_exercise_topics")
        ),
    )
    op.create_index(
        "ix_exercise_topics_topic_id", "exercise_topics", ["topic_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_exercise_topics_topic_id", table_name="exercise_topics")
    op.drop_table("exercise_topics")
