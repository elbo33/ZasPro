"""mapping and review

Revision ID: 0004_mapping_and_review
Revises: 0003_exercise_own_figure_count
Create Date: 2026-08-27 01:49:02.315734

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0004_mapping_and_review'
down_revision: str | Sequence[str] | None = '0003_exercise_own_figure_count'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('chunk_mappings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('source_chunk_id', sa.Integer(), nullable=False),
    sa.Column('topic_id', sa.Integer(), nullable=True),
    sa.Column('content_type', sa.Enum('EXPLANATION', 'DEFINITION', 'FORMULA', 'EXAMPLE', 'EXERCISE', 'SOLUTION', 'THEOREM', 'NOTE', 'WARNING', name='content_type', native_enum=False), nullable=False),
    sa.Column('difficulty', sa.Integer(), nullable=True),
    sa.Column('confidence', sa.Float(), nullable=False),
    sa.Column('mapping_status', sa.Enum('AI_SUGGESTED', 'REVIEW_REQUIRED', 'APPROVED', 'REJECTED', name='mapping_status', native_enum=False), nullable=False),
    sa.Column('rationale', sa.Text(), nullable=True),
    sa.Column('model', sa.String(length=64), nullable=True),
    sa.Column('prompt_version', sa.String(length=32), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['source_chunk_id'], ['source_chunks.id'], name=op.f('fk_chunk_mappings_source_chunk_id_source_chunks'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['topic_id'], ['topics.id'], name=op.f('fk_chunk_mappings_topic_id_topics'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_chunk_mappings')),
    sa.UniqueConstraint('source_chunk_id', name='uq_chunk_mappings_chunk')
    )
    op.create_table('review_items',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('item_type', sa.Enum('CURRICULUM_MAPPING', 'FORMULA', 'EXERCISE', 'MISCONCEPTION', 'MERGE_CANDIDATE', 'EXTRACTION_CONFLICT', 'NORMALISATION_FAILURE', name='review_item_type', native_enum=False), nullable=False),
    sa.Column('ref_table', sa.String(length=64), nullable=False),
    sa.Column('ref_id', sa.Integer(), nullable=False),
    sa.Column('status', sa.Enum('OPEN', 'APPROVED', 'REJECTED', name='review_status', native_enum=False), nullable=False),
    sa.Column('risk', sa.Float(), nullable=False),
    sa.Column('confidence', sa.Float(), nullable=True),
    sa.Column('title', sa.Text(), nullable=False),
    sa.Column('topic_id', sa.Integer(), nullable=True),
    sa.Column('source_document_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('resolved_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['source_document_id'], ['source_documents.id'], name=op.f('fk_review_items_source_document_id_source_documents'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['topic_id'], ['topics.id'], name=op.f('fk_review_items_topic_id_topics'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_review_items')),
    sa.UniqueConstraint('item_type', 'ref_table', 'ref_id', name='uq_review_items_ref')
    )
    op.create_index(op.f('ix_review_items_risk'), 'review_items', ['risk'], unique=False)
    op.create_index(op.f('ix_review_items_status'), 'review_items', ['status'], unique=False)
    op.create_table('review_decisions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('review_item_id', sa.Integer(), nullable=False),
    sa.Column('reviewer', sa.String(length=120), nullable=False),
    sa.Column('decision', sa.Enum('APPROVE', 'REJECT', 'EDIT', name='review_decision_type', native_enum=False), nullable=False),
    sa.Column('reason_code', sa.Enum('WRONG_TOPIC', 'WRONG_CONTENT_TYPE', 'NOT_CURRICULUM', 'AMBIGUOUS', 'LOW_QUALITY_SOURCE', 'OTHER', name='review_reason_code', native_enum=False), nullable=True),
    sa.Column('prior_status', sa.String(length=32), nullable=False),
    sa.Column('note', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("decision <> 'REJECT' OR reason_code IS NOT NULL", name=op.f('ck_review_decisions_ck_review_decisions_reject_needs_reason')),
    sa.ForeignKeyConstraint(['review_item_id'], ['review_items.id'], name=op.f('fk_review_decisions_review_item_id_review_items'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_review_decisions'))
    )


def downgrade() -> None:
    op.drop_table('review_decisions')
    op.drop_index(op.f('ix_review_items_status'), table_name='review_items')
    op.drop_index(op.f('ix_review_items_risk'), table_name='review_items')
    op.drop_table('review_items')
    op.drop_table('chunk_mappings')
