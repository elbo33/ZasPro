"""knowledge tables (M4)

Revision ID: 0009_knowledge_tables
Revises: 0008_exercise_topics
Create Date: 2026-08-28 00:55:20.044777

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0009_knowledge_tables'
down_revision: str | Sequence[str] | None = '0008_exercise_topics'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('concepts',
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('explanation', sa.Text(), nullable=True),
    sa.Column('difficulty', sa.Integer(), nullable=True),
    sa.Column('order_index', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('topic_id', sa.Integer(), nullable=False),
    sa.Column('source_chunk_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('verification_status', sa.Enum('DRAFT', 'AI_GENERATED', 'PENDING_REVIEW', 'AUTO_VERIFIED', 'APPROVED', 'REJECTED', name='verification_status', native_enum=False), nullable=False),
    sa.ForeignKeyConstraint(['topic_id'], ['topics.id'], name=op.f('fk_concepts_topic_id_topics'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_concepts'))
    )
    op.create_index(op.f('ix_concepts_topic_id'), 'concepts', ['topic_id'], unique=False)
    op.create_table('formulas',
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('latex_raw', sa.Text(), nullable=False),
    sa.Column('latex_normalised', sa.Text(), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('conditions', sa.Text(), nullable=True),
    sa.Column('order_index', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('topic_id', sa.Integer(), nullable=False),
    sa.Column('source_chunk_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('verification_status', sa.Enum('DRAFT', 'AI_GENERATED', 'PENDING_REVIEW', 'AUTO_VERIFIED', 'APPROVED', 'REJECTED', name='verification_status', native_enum=False), nullable=False),
    sa.ForeignKeyConstraint(['topic_id'], ['topics.id'], name=op.f('fk_formulas_topic_id_topics'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_formulas'))
    )
    op.create_index(op.f('ix_formulas_topic_id'), 'formulas', ['topic_id'], unique=False)
    op.create_table('knowledge_flags',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('topic_id', sa.Integer(), nullable=False),
    sa.Column('kind', sa.Enum('CONFLICT', 'GAP', name='flag_kind', native_enum=False), nullable=False),
    sa.Column('item_kind', sa.String(length=32), nullable=False),
    sa.Column('detail', sa.Text(), nullable=False),
    sa.Column('source_chunk_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('resolved', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['topic_id'], ['topics.id'], name=op.f('fk_knowledge_flags_topic_id_topics'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_knowledge_flags'))
    )
    op.create_index(op.f('ix_knowledge_flags_topic_id'), 'knowledge_flags', ['topic_id'], unique=False)
    op.create_table('learning_objectives',
    sa.Column('statement', sa.Text(), nullable=False),
    sa.Column('bloom_level', sa.String(length=32), nullable=True),
    sa.Column('order_index', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('topic_id', sa.Integer(), nullable=False),
    sa.Column('source_chunk_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('verification_status', sa.Enum('DRAFT', 'AI_GENERATED', 'PENDING_REVIEW', 'AUTO_VERIFIED', 'APPROVED', 'REJECTED', name='verification_status', native_enum=False), nullable=False),
    sa.ForeignKeyConstraint(['topic_id'], ['topics.id'], name=op.f('fk_learning_objectives_topic_id_topics'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_learning_objectives'))
    )
    op.create_index(op.f('ix_learning_objectives_topic_id'), 'learning_objectives', ['topic_id'], unique=False)
    op.create_table('methods',
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('when_to_use', sa.Text(), nullable=True),
    sa.Column('steps', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('order_index', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('topic_id', sa.Integer(), nullable=False),
    sa.Column('source_chunk_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('verification_status', sa.Enum('DRAFT', 'AI_GENERATED', 'PENDING_REVIEW', 'AUTO_VERIFIED', 'APPROVED', 'REJECTED', name='verification_status', native_enum=False), nullable=False),
    sa.ForeignKeyConstraint(['topic_id'], ['topics.id'], name=op.f('fk_methods_topic_id_topics'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_methods'))
    )
    op.create_index(op.f('ix_methods_topic_id'), 'methods', ['topic_id'], unique=False)
    op.create_table('misconceptions',
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('incorrect_reasoning', sa.Text(), nullable=True),
    sa.Column('correct_reasoning', sa.Text(), nullable=True),
    sa.Column('example', sa.Text(), nullable=True),
    sa.Column('severity', sa.Integer(), nullable=True),
    sa.Column('source_kind', sa.Enum('MARKING_SCHEME', 'INFORMATOR', 'AGENT_INFERENCE', 'UNSOURCED', name='misconception_source', native_enum=False), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('topic_id', sa.Integer(), nullable=False),
    sa.Column('source_chunk_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('verification_status', sa.Enum('DRAFT', 'AI_GENERATED', 'PENDING_REVIEW', 'AUTO_VERIFIED', 'APPROVED', 'REJECTED', name='verification_status', native_enum=False), nullable=False),
    sa.ForeignKeyConstraint(['topic_id'], ['topics.id'], name=op.f('fk_misconceptions_topic_id_topics'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_misconceptions'))
    )
    op.create_index(op.f('ix_misconceptions_topic_id'), 'misconceptions', ['topic_id'], unique=False)
    op.create_table('examples',
    sa.Column('concept_id', sa.Integer(), nullable=True),
    sa.Column('statement', sa.Text(), nullable=False),
    sa.Column('worked_solution', sa.Text(), nullable=True),
    sa.Column('difficulty', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('topic_id', sa.Integer(), nullable=False),
    sa.Column('source_chunk_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('verification_status', sa.Enum('DRAFT', 'AI_GENERATED', 'PENDING_REVIEW', 'AUTO_VERIFIED', 'APPROVED', 'REJECTED', name='verification_status', native_enum=False), nullable=False),
    sa.ForeignKeyConstraint(['concept_id'], ['concepts.id'], name=op.f('fk_examples_concept_id_concepts'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['topic_id'], ['topics.id'], name=op.f('fk_examples_topic_id_topics'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_examples'))
    )
    op.create_index(op.f('ix_examples_topic_id'), 'examples', ['topic_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_examples_topic_id'), table_name='examples')
    op.drop_table('examples')
    op.drop_index(op.f('ix_misconceptions_topic_id'), table_name='misconceptions')
    op.drop_table('misconceptions')
    op.drop_index(op.f('ix_methods_topic_id'), table_name='methods')
    op.drop_table('methods')
    op.drop_index(op.f('ix_learning_objectives_topic_id'), table_name='learning_objectives')
    op.drop_table('learning_objectives')
    op.drop_index(op.f('ix_knowledge_flags_topic_id'), table_name='knowledge_flags')
    op.drop_table('knowledge_flags')
    op.drop_index(op.f('ix_formulas_topic_id'), table_name='formulas')
    op.drop_table('formulas')
    op.drop_index(op.f('ix_concepts_topic_id'), table_name='concepts')
    op.drop_table('concepts')
