"""review calibration: audit_sample, mapping_confidence

Revision ID: 0005_review_calibration
Revises: 0004_mapping_and_review
Create Date: 2026-08-27 03:00:02.139039

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_review_calibration"
down_revision: str | Sequence[str] | None = "0004_mapping_and_review"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # mapping confidence frozen onto each decision, for the agreement-vs-
    # confidence calibration curve
    op.add_column(
        "review_decisions",
        sa.Column("mapping_confidence", sa.Float(), nullable=True),
    )
    # items queued by the permanent audit sampler rather than by low confidence
    op.add_column(
        "review_items",
        sa.Column(
            "audit_sample",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.create_index(
        op.f("ix_review_items_audit_sample"), "review_items", ["audit_sample"]
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_review_items_audit_sample"), table_name="review_items")
    op.drop_column("review_items", "audit_sample")
    op.drop_column("review_decisions", "mapping_confidence")
