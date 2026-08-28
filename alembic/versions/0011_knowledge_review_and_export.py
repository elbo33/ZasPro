"""knowledge_extractions + KNOWLEDGE_SPEC review type (M4)

Revision ID: 0011_knowledge_review_and_export
Revises: 0010_misconception_distractor
Create Date: 2026-08-28 02:43:58.473121

`knowledge_extractions` is one row per topic: last extraction + approval/export
state (ADR 0011 — git holds the record, the DB is the working store).

`ReviewItemType.KNOWLEDGE_SPEC` (one review card per topic) needs no DDL —
`review_item_type` is `native_enum=False` (VARCHAR, no CHECK) and the value fits
the existing width.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011_knowledge_review_and_export"
down_revision: str | Sequence[str] | None = "0010_misconception_distractor"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "knowledge_extractions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("topic_id", sa.Integer(), nullable=False),
        sa.Column("agent_name", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=64), nullable=True),
        sa.Column("prompt_version", sa.String(length=32), nullable=False),
        sa.Column("exercises", sa.Integer(), nullable=False),
        sa.Column(
            "extracted_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("review_item_id", sa.Integer(), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("approved_by", sa.String(length=120), nullable=True),
        sa.Column("exported_at", sa.DateTime(), nullable=True),
        sa.Column("export_path", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["review_item_id"], ["review_items.id"],
            name=op.f("fk_knowledge_extractions_review_item_id_review_items"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["topic_id"], ["topics.id"],
            name=op.f("fk_knowledge_extractions_topic_id_topics"), ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_knowledge_extractions")),
    )
    op.create_index(
        op.f("ix_knowledge_extractions_topic_id"),
        "knowledge_extractions", ["topic_id"], unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_knowledge_extractions_topic_id"), table_name="knowledge_extractions"
    )
    op.drop_table("knowledge_extractions")
