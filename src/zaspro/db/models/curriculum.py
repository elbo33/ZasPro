"""Curriculum tables (SPEC §5).

`units` and `topics` form an adjacency-list tree via `topics.parent_id`. The
tree is small, shallow and read-only after seeding, so adjacency is the right
representation — reparenting is a single-row update that cannot leave the tree
inconsistent (SPEC §5).

`topic_prerequisites` is a *separate* structure: a DAG over topics, not the
curriculum tree. Acyclicity is enforced at write time by a trigger created in
the migration (`0001`), using PostgreSQL's `CYCLE` clause — not by trusting the
seeding process.
"""

from __future__ import annotations

import enum

from sqlalchemy import (
    CheckConstraint,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from zaspro.db.base import Base, Code, ShortName, Slug, TimestampMixin


class TopicLevel(str, enum.Enum):
    PODSTAWOWY = "podstawowy"
    ROZSZERZONY = "rozszerzony"


class TopicStatus(str, enum.Enum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"


class PrerequisiteImportance(str, enum.Enum):
    REQUIRED = "required"
    RECOMMENDED = "recommended"
    HELPFUL = "helpful"


def _enum(py_enum: type[enum.Enum], name: str) -> Enum:
    # native_enum=False -> VARCHAR + CHECK; painless to extend in later migrations.
    return Enum(py_enum, name=name, native_enum=False, validate_strings=True)


class Subject(Base, TimestampMixin):
    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[ShortName]
    slug: Mapped[Slug] = mapped_column(unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(8), default="pl")
    # Curriculum levels this subject defines, e.g. "podstawowy, rozszerzony".
    level: Mapped[ShortName]

    units: Mapped[list[Unit]] = relationship(
        back_populates="subject", order_by="Unit.order_index", cascade="all, delete-orphan"
    )


class Unit(Base, TimestampMixin):
    __tablename__ = "units"
    __table_args__ = (
        UniqueConstraint("subject_id", "code", name="uq_units_subject_code"),
        UniqueConstraint("subject_id", "slug", name="uq_units_subject_slug"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"))
    code: Mapped[Code]  # Roman section numeral, e.g. "VIII"
    slug: Mapped[Slug]
    name: Mapped[ShortName]
    description: Mapped[str | None] = mapped_column(Text)
    order_index: Mapped[int] = mapped_column(Integer)

    subject: Mapped[Subject] = relationship(back_populates="units")
    topics: Mapped[list[Topic]] = relationship(
        back_populates="unit", order_by="(Topic.level, Topic.order_index)", cascade="all, delete-orphan"
    )


class Topic(Base, TimestampMixin):
    __tablename__ = "topics"
    __table_args__ = (
        UniqueConstraint("unit_id", "slug", name="uq_topics_unit_slug"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    unit_id: Mapped[int] = mapped_column(ForeignKey("units.id", ondelete="CASCADE"))
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("topics.id", ondelete="CASCADE"))

    name: Mapped[str] = mapped_column(Text)  # the requirement prose
    slug: Mapped[Slug]
    description: Mapped[str | None] = mapped_column(Text)
    statement_latex: Mapped[str | None] = mapped_column(Text)  # NULL == no formula

    level: Mapped[TopicLevel] = mapped_column(_enum(TopicLevel, "topic_level"))
    order_index: Mapped[int] = mapped_column(Integer)
    # Link back to the podstawa programowa numbering; unique where present.
    official_requirement_code: Mapped[str | None] = mapped_column(String(32), unique=True)
    status: Mapped[TopicStatus] = mapped_column(
        _enum(TopicStatus, "topic_status"), default=TopicStatus.ACTIVE
    )

    unit: Mapped[Unit] = relationship(back_populates="topics")
    children: Mapped[list[Topic]] = relationship(
        back_populates="parent", cascade="all, delete-orphan"
    )
    parent: Mapped[Topic | None] = relationship(back_populates="children", remote_side="Topic.id")

    prerequisites: Mapped[list[TopicPrerequisite]] = relationship(
        back_populates="topic",
        foreign_keys="TopicPrerequisite.topic_id",
        cascade="all, delete-orphan",
    )


class TopicPrerequisite(Base):
    __tablename__ = "topic_prerequisites"
    __table_args__ = (
        CheckConstraint("topic_id <> prerequisite_topic_id", name="no_self_prerequisite"),
    )

    topic_id: Mapped[int] = mapped_column(
        ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True
    )
    prerequisite_topic_id: Mapped[int] = mapped_column(
        ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True
    )
    importance: Mapped[PrerequisiteImportance] = mapped_column(
        _enum(PrerequisiteImportance, "prerequisite_importance"),
        default=PrerequisiteImportance.REQUIRED,
    )
    reason: Mapped[str | None] = mapped_column(Text)

    topic: Mapped[Topic] = relationship(back_populates="prerequisites", foreign_keys=[topic_id])
    prerequisite: Mapped[Topic] = relationship(foreign_keys=[prerequisite_topic_id])
