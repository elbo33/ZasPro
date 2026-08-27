"""review_items.input_defect

Revision ID: 0007_review_input_defect
Revises: 0006_multitopic_mapping
Create Date: 2026-08-28 09:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_review_input_defect"
down_revision: str | Sequence[str] | None = "0006_multitopic_mapping"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "review_items",
        sa.Column(
            "input_defect",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_review_items_input_defect", "review_items", ["input_defect"]
    )


def downgrade() -> None:
    op.drop_index("ix_review_items_input_defect", table_name="review_items")
    op.drop_column("review_items", "input_defect")
