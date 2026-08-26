"""ingestion exercises jobs

Revision ID: 0002_ingestion_exercises_jobs
Revises: 0001_curriculum_and_sources
Create Date: 2026-08-27 00:46:53.090986

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0002_ingestion_exercises_jobs'
down_revision: str | Sequence[str] | None = '0001_curriculum_and_sources'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('jobs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('job_type', sa.Enum('INGEST_DOCUMENT', 'CONVERT_DOCX', 'EXTRACT_MEDIA', 'RENDER_VECTOR_FIGURE', 'SEGMENT_EXERCISES', 'NORMALISE_LATEX', 'EXTRACT_PDF_TEXT', 'CHUNK_DOCUMENT', 'CLASSIFY_CHUNK', 'MAP_CHUNK', 'EXTRACT_KNOWLEDGE', 'MERGE_CANDIDATES', 'VERIFY_FORMULA', 'GENERATE_EXERCISE', 'VERIFY_EXERCISE', 'ASSEMBLE_KNOWLEDGE_SPEC', 'GENERATE_EPISODE_PLAN', 'GENERATE_SCENE_PLAN', 'RUN_QA', name='job_type', native_enum=False), nullable=False),
    sa.Column('status', sa.Enum('PENDING', 'RUNNING', 'SUCCEEDED', 'FAILED', name='job_status', native_enum=False), nullable=False),
    sa.Column('attempts', sa.Integer(), nullable=False),
    sa.Column('max_attempts', sa.Integer(), nullable=False),
    sa.Column('input', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('output', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('error', sa.Text(), nullable=True),
    sa.Column('model', sa.String(length=64), nullable=True),
    sa.Column('prompt_version', sa.String(length=32), nullable=True),
    sa.Column('pipeline_version', sa.String(length=32), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_jobs'))
    )
    op.create_index(op.f('ix_jobs_status'), 'jobs', ['status'], unique=False)
    op.create_table('source_documents',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('source_id', sa.Integer(), nullable=False),
    sa.Column('file_ref', sa.String(length=255), nullable=False),
    sa.Column('page_count', sa.Integer(), nullable=True),
    sa.Column('extraction_status', sa.Enum('PENDING', 'CONVERTED', 'SEGMENTED', 'VALIDATED', 'FAILED', name='extraction_status', native_enum=False), nullable=False),
    sa.Column('variant_code', sa.String(length=8), nullable=True),
    sa.Column('paper_version', sa.String(length=2), nullable=True),
    sa.Column('session_code', sa.String(length=16), nullable=True),
    sa.Column('sibling_docx_ref', sa.String(length=255), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['source_id'], ['sources.id'], name=op.f('fk_source_documents_source_id_sources'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_source_documents')),
    sa.UniqueConstraint('file_ref', name=op.f('uq_source_documents_file_ref'))
    )
    op.create_table('figures',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('source_document_id', sa.Integer(), nullable=False),
    sa.Column('page', sa.Integer(), nullable=True),
    sa.Column('bbox', sa.String(length=120), nullable=True),
    sa.Column('image_ref', sa.Text(), nullable=True),
    sa.Column('source_format', sa.Enum('RASTER', 'WMF', 'WORD_SHAPE', name='source_format', native_enum=False), nullable=False),
    sa.Column('render_status', sa.Enum('PENDING', 'COMPLETE', 'FAILED', name='render_status', native_enum=False), nullable=False),
    sa.Column('caption', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['source_document_id'], ['source_documents.id'], name=op.f('fk_figures_source_document_id_source_documents'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_figures'))
    )
    op.create_table('source_chunks',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('source_document_id', sa.Integer(), nullable=False),
    sa.Column('page', sa.Integer(), nullable=True),
    sa.Column('chapter', sa.String(length=255), nullable=True),
    sa.Column('section', sa.String(length=255), nullable=True),
    sa.Column('heading', sa.String(length=255), nullable=True),
    sa.Column('content_type', sa.Enum('EXPLANATION', 'DEFINITION', 'FORMULA', 'EXAMPLE', 'EXERCISE', 'SOLUTION', 'THEOREM', 'NOTE', 'WARNING', name='content_type', native_enum=False), nullable=False),
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('latex', sa.Text(), nullable=True),
    sa.Column('order_index', sa.Integer(), nullable=False),
    sa.Column('extraction_method', sa.Enum('pandoc_omml', 'pdf_text', 'pdf_vision', 'manual', name='extraction_method', native_enum=False), nullable=False),
    sa.Column('confidence', sa.Float(), nullable=True),
    sa.ForeignKeyConstraint(['source_document_id'], ['source_documents.id'], name=op.f('fk_source_chunks_source_document_id_source_documents'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_source_chunks')),
    sa.UniqueConstraint('source_document_id', 'order_index', name='uq_source_chunks_doc_order')
    )
    op.create_table('exercises',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('source_document_id', sa.Integer(), nullable=True),
    sa.Column('topic_id', sa.Integer(), nullable=True),
    sa.Column('parent_exercise_id', sa.Integer(), nullable=True),
    sa.Column('exercise_number', sa.String(length=16), nullable=False),
    sa.Column('statement', sa.Text(), nullable=False),
    sa.Column('statement_latex_raw', sa.Text(), nullable=True),
    sa.Column('statement_latex_normalised', sa.Text(), nullable=True),
    sa.Column('difficulty', sa.Integer(), nullable=True),
    sa.Column('exercise_type', sa.String(length=64), nullable=True),
    sa.Column('solution', sa.Text(), nullable=True),
    sa.Column('solution_steps', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('final_answer_repr', sa.Text(), nullable=True),
    sa.Column('skills_required', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('origin', sa.Enum('OFFICIAL', 'LICENSED', 'OPEN', 'HUMAN_CREATED', 'AI_GENERATED', name='exercise_origin', native_enum=False), nullable=False),
    sa.Column('verbatim_ok', sa.Boolean(), nullable=False),
    sa.Column('variant_group_id', sa.String(length=64), nullable=True),
    sa.Column('points_available', sa.Integer(), nullable=True),
    sa.Column('expected_figure_count', sa.Integer(), nullable=False),
    sa.Column('verification_status', sa.Enum('DRAFT', 'AI_GENERATED', 'PENDING_REVIEW', 'AUTO_VERIFIED', 'APPROVED', 'REJECTED', name='verification_status', native_enum=False), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['parent_exercise_id'], ['exercises.id'], name=op.f('fk_exercises_parent_exercise_id_exercises'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['source_document_id'], ['source_documents.id'], name=op.f('fk_exercises_source_document_id_source_documents'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['topic_id'], ['topics.id'], name=op.f('fk_exercises_topic_id_topics'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_exercises')),
    sa.UniqueConstraint('source_document_id', 'exercise_number', name='uq_exercises_doc_number')
    )
    op.create_table('exercise_figures',
    sa.Column('exercise_id', sa.Integer(), nullable=False),
    sa.Column('figure_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['exercise_id'], ['exercises.id'], name=op.f('fk_exercise_figures_exercise_id_exercises'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['figure_id'], ['figures.id'], name=op.f('fk_exercise_figures_figure_id_figures'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('exercise_id', 'figure_id', name=op.f('pk_exercise_figures'))
    )


def downgrade() -> None:
    op.drop_table('exercise_figures')
    op.drop_table('exercises')
    op.drop_table('source_chunks')
    op.drop_table('figures')
    op.drop_table('source_documents')
    op.drop_index(op.f('ix_jobs_status'), table_name='jobs')
    op.drop_table('jobs')
