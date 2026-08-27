"""multi-topic mapping: is_primary + partial unique index

Revision ID: 0006_multitopic_mapping
Revises: 0005_review_calibration
Create Date: 2026-08-27 16:27:30.058786

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_multitopic_mapping"
down_revision: str | Sequence[str] | None = "0005_review_calibration"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # existing rows are all the single mapping for their chunk -> primary
    op.add_column(
        "chunk_mappings",
        sa.Column(
            "is_primary", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
    )
    # the old "one row per chunk" constraint is replaced by "one PRIMARY per chunk"
    op.drop_constraint("uq_chunk_mappings_chunk", "chunk_mappings", type_="unique")
    op.create_index(
        "uq_chunk_mappings_primary",
        "chunk_mappings",
        ["source_chunk_id"],
        unique=True,
        postgresql_where=sa.text("is_primary"),
    )
    op.create_index("ix_chunk_mappings_is_primary", "chunk_mappings", ["is_primary"])
    op.create_index(
        "ix_chunk_mappings_source_chunk_id", "chunk_mappings", ["source_chunk_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_chunk_mappings_source_chunk_id", table_name="chunk_mappings")
    op.drop_index("ix_chunk_mappings_is_primary", table_name="chunk_mappings")
    op.drop_index("uq_chunk_mappings_primary", table_name="chunk_mappings")
    # collapsing back to one row per chunk: drop non-primary rows first
    op.execute("DELETE FROM chunk_mappings WHERE NOT is_primary")
    op.create_unique_constraint(
        "uq_chunk_mappings_chunk", "chunk_mappings", ["source_chunk_id"]
    )
    op.drop_column("chunk_mappings", "is_primary")
