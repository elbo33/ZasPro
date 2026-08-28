"""teaching sections; knowledge spec is section-scoped (M4, ADR 0012)

Revision ID: 0013_teaching_sections
Revises: 0012_knowledge_provenance
Create Date: 2026-08-28 18:00:00.000000

The Knowledge Agent now writes one spec per teaching section, from subject
knowledge, scoped by the section's requirement codes. Exercises are out of the
knowledge path entirely: no source references, no provenance labels, no flags.

* new `sections` + `section_requirements`
* the six knowledge item tables move from `topic_id` to `section_id`; drop
  `provenance`, `source_chunk_ids`, and `misconceptions.distractor`
* drop `knowledge_flags`
* `knowledge_extractions` -> `section_specs` (section-keyed)

The knowledge tables are truncated on upgrade — their content (two topics from
the abandoned exercise-based path) is disposable and regenerated per section.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013_teaching_sections"
down_revision: str | Sequence[str] | None = "0012_knowledge_provenance"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ITEM_TABLES = ("concepts", "formulas", "methods", "examples", "misconceptions",
                "learning_objectives")


def upgrade() -> None:
    op.create_table(
        "sections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("subject_id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("scope", sa.Text(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"],
                                name=op.f("fk_sections_subject_id_subjects"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sections")),
        sa.UniqueConstraint("slug", name=op.f("uq_sections_slug")),
        sa.UniqueConstraint("subject_id", "order_index", name="uq_sections_subject_order"),
    )
    op.create_table(
        "section_requirements",
        sa.Column("section_id", sa.Integer(), nullable=False),
        sa.Column("topic_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["section_id"], ["sections.id"],
                                name=op.f("fk_section_requirements_section_id_sections"),
                                ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"],
                                name=op.f("fk_section_requirements_topic_id_topics"),
                                ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("section_id", "topic_id", name=op.f("pk_section_requirements")),
    )
    op.create_index("ix_section_requirements_topic_id", "section_requirements", ["topic_id"])

    op.execute(
        "TRUNCATE concepts, formulas, methods, examples, misconceptions, "
        "learning_objectives, knowledge_flags, knowledge_extractions CASCADE"
    )

    for t in _ITEM_TABLES:
        op.add_column(t, sa.Column("section_id", sa.Integer(), nullable=False))
        op.create_foreign_key(op.f(f"fk_{t}_section_id_sections"), t, "sections",
                              ["section_id"], ["id"], ondelete="CASCADE")
        op.create_index(f"ix_{t}_section_id", t, ["section_id"])
        op.drop_column(t, "topic_id")
        op.drop_column(t, "provenance")
        op.drop_column(t, "source_chunk_ids")
    for t in ("examples", "misconceptions"):
        op.add_column(t, sa.Column("order_index", sa.Integer(), nullable=False,
                                   server_default="0"))
    op.drop_column("misconceptions", "distractor")

    op.drop_table("knowledge_flags")
    op.drop_table("knowledge_extractions")

    op.create_table(
        "section_specs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("section_id", sa.Integer(), nullable=False),
        sa.Column("agent_name", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=64), nullable=True),
        sa.Column("prompt_version", sa.String(length=32), nullable=False),
        sa.Column("written_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("review_item_id", sa.Integer(), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("approved_by", sa.String(length=120), nullable=True),
        sa.Column("exported_at", sa.DateTime(), nullable=True),
        sa.Column("export_path", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["section_id"], ["sections.id"],
                                name=op.f("fk_section_specs_section_id_sections"),
                                ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["review_item_id"], ["review_items.id"],
                                name=op.f("fk_section_specs_review_item_id_review_items"),
                                ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_section_specs")),
    )
    op.create_index(op.f("ix_section_specs_section_id"), "section_specs",
                    ["section_id"], unique=True)


def downgrade() -> None:
    op.drop_table("section_specs")
    op.create_table(
        "knowledge_extractions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("topic_id", sa.Integer(), sa.ForeignKey("topics.id", ondelete="CASCADE"),
                  unique=True),
        sa.Column("agent_name", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=64)),
        sa.Column("prompt_version", sa.String(length=32), nullable=False),
        sa.Column("exercises", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("extracted_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("review_item_id", sa.Integer(),
                  sa.ForeignKey("review_items.id", ondelete="SET NULL")),
        sa.Column("approved_at", sa.DateTime()),
        sa.Column("approved_by", sa.String(length=120)),
        sa.Column("exported_at", sa.DateTime()),
        sa.Column("export_path", sa.String(length=255)),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "knowledge_flags",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("topic_id", sa.Integer(), sa.ForeignKey("topics.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("item_kind", sa.String(length=32), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("source_chunk_ids", sa.dialects.postgresql.JSONB()),
        sa.Column("resolved", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
    )
    op.add_column("misconceptions", sa.Column("distractor", sa.String(length=255)))
    for t in ("misconceptions", "examples"):
        op.drop_column(t, "order_index")
    for t in reversed(_ITEM_TABLES):
        op.add_column(t, sa.Column("source_chunk_ids", sa.dialects.postgresql.JSONB()))
        op.add_column(t, sa.Column("provenance", sa.String(length=32), nullable=False,
                                   server_default="AGENT_KNOWLEDGE"))
        op.add_column(t, sa.Column("topic_id", sa.Integer(), nullable=False,
                                   server_default="0"))
        op.create_foreign_key(op.f(f"fk_{t}_topic_id_topics"), t, "topics",
                              ["topic_id"], ["id"], ondelete="CASCADE")
        op.drop_index(f"ix_{t}_section_id", table_name=t)
        op.drop_column(t, "section_id")
    op.drop_index("ix_section_requirements_topic_id", table_name="section_requirements")
    op.drop_table("section_requirements")
    op.drop_table("sections")
