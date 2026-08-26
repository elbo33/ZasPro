"""curriculum and sources

The M1 migration batch (SPEC §5): the curriculum tree (`subjects`, `units`,
`topics`) as an adjacency list, the `topic_prerequisites` DAG with a
write-time acyclicity trigger, and `sources`.

No pgvector (SPEC §15: never in a migration).

Revision ID: 0001_curriculum_and_sources
Revises:
Create Date: 2026-08-27
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_curriculum_and_sources"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Acyclicity for topic_prerequisites, enforced at write time (SPEC §5) with
# PostgreSQL's CYCLE clause rather than trusting the seeding process. An edge
# `topic -> prerequisite` means "topic needs prerequisite first"; the edge is
# rejected if `prerequisite` can already reach `topic` by following prerequisite
# edges. The CYCLE clause also stops the check itself looping if the existing
# data is somehow already cyclic.
_CYCLE_GUARD = """
CREATE FUNCTION topic_prerequisites_reject_cycle() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF EXISTS (
        WITH RECURSIVE walk (id) AS (
            SELECT NEW.prerequisite_topic_id
            UNION ALL
            SELECT tp.prerequisite_topic_id
            FROM topic_prerequisites tp
            JOIN walk w ON tp.topic_id = w.id
        ) CYCLE id SET is_cycle USING cycle_path
        SELECT 1 FROM walk WHERE id = NEW.topic_id
    ) THEN
        RAISE EXCEPTION
            'prerequisite edge % -> % would create a cycle in topic_prerequisites',
            NEW.topic_id, NEW.prerequisite_topic_id
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER topic_prerequisites_no_cycle
    BEFORE INSERT OR UPDATE ON topic_prerequisites
    FOR EACH ROW EXECUTE FUNCTION topic_prerequisites_reject_cycle();
"""

_CYCLE_GUARD_DOWN = """
DROP TRIGGER IF EXISTS topic_prerequisites_no_cycle ON topic_prerequisites;
DROP FUNCTION IF EXISTS topic_prerequisites_reject_cycle();
"""


def upgrade() -> None:
    op.create_table(
        "sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("author", sa.String(length=255), nullable=True),
        sa.Column("publisher", sa.String(length=255), nullable=False),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column(
            "source_type",
            sa.Enum(
                "PODSTAWA_PROGRAMOWA", "OFFICIAL_CKE", "EXAM", "MARKING_SCHEME",
                "FORMULA_SHEET", "TEXTBOOK", "OPEN_EDUCATIONAL_RESOURCE",
                "USER_PROVIDED", "OTHER",
                name="source_type", native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "licence_status",
            sa.Enum("MATERIAL_URZEDOWY", "CKE_UNSPECIFIED", name="licence_status", native_enum=False),
            nullable=False,
        ),
        sa.Column("verbatim_ok", sa.Boolean(), nullable=False),
        sa.Column("reuse_notes", sa.Text(), nullable=True),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("file_ref", sa.String(length=255), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "processing_status",
            sa.Enum("PENDING", "INGESTED", "FAILED", name="processing_status", native_enum=False),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sources")),
        sa.UniqueConstraint("file_ref", name=op.f("uq_sources_file_ref")),
    )
    op.create_table(
        "subjects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("language", sa.String(length=8), nullable=False),
        sa.Column("level", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_subjects")),
        sa.UniqueConstraint("slug", name=op.f("uq_subjects_slug")),
    )
    op.create_table(
        "units",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("subject_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["subject_id"], ["subjects.id"],
            name=op.f("fk_units_subject_id_subjects"), ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_units")),
        sa.UniqueConstraint("subject_id", "code", name="uq_units_subject_code"),
        sa.UniqueConstraint("subject_id", "slug", name="uq_units_subject_slug"),
    )
    op.create_table(
        "topics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("unit_id", sa.Integer(), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("statement_latex", sa.Text(), nullable=True),
        sa.Column(
            "level",
            sa.Enum("PODSTAWOWY", "ROZSZERZONY", name="topic_level", native_enum=False),
            nullable=False,
        ),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("official_requirement_code", sa.String(length=32), nullable=True),
        sa.Column(
            "status",
            sa.Enum("ACTIVE", "DEPRECATED", name="topic_status", native_enum=False),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["parent_id"], ["topics.id"],
            name=op.f("fk_topics_parent_id_topics"), ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["unit_id"], ["units.id"],
            name=op.f("fk_topics_unit_id_units"), ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_topics")),
        sa.UniqueConstraint(
            "official_requirement_code", name=op.f("uq_topics_official_requirement_code")
        ),
        sa.UniqueConstraint("unit_id", "slug", name="uq_topics_unit_slug"),
    )
    op.create_table(
        "topic_prerequisites",
        sa.Column("topic_id", sa.Integer(), nullable=False),
        sa.Column("prerequisite_topic_id", sa.Integer(), nullable=False),
        sa.Column(
            "importance",
            sa.Enum(
                "REQUIRED", "RECOMMENDED", "HELPFUL",
                name="prerequisite_importance", native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "topic_id <> prerequisite_topic_id",
            name=op.f("ck_topic_prerequisites_no_self_prerequisite"),
        ),
        sa.ForeignKeyConstraint(
            ["prerequisite_topic_id"], ["topics.id"],
            name=op.f("fk_topic_prerequisites_prerequisite_topic_id_topics"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["topic_id"], ["topics.id"],
            name=op.f("fk_topic_prerequisites_topic_id_topics"), ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "topic_id", "prerequisite_topic_id", name=op.f("pk_topic_prerequisites")
        ),
    )
    op.execute(_CYCLE_GUARD)


def downgrade() -> None:
    op.execute(_CYCLE_GUARD_DOWN)
    op.drop_table("topic_prerequisites")
    op.drop_table("topics")
    op.drop_table("units")
    op.drop_table("subjects")
    op.drop_table("sources")
