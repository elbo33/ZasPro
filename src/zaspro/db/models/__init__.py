"""ORM models. Import this module so Alembic's autogenerate sees every table."""

from zaspro.db.models.curriculum import (
    PrerequisiteImportance,
    Subject,
    Topic,
    TopicLevel,
    TopicPrerequisite,
    TopicStatus,
    Unit,
)
from zaspro.db.models.sources import (
    LicenceStatus,
    ProcessingStatus,
    Source,
    SourceType,
)

__all__ = [
    "Subject",
    "Unit",
    "Topic",
    "TopicPrerequisite",
    "TopicLevel",
    "TopicStatus",
    "PrerequisiteImportance",
    "Source",
    "SourceType",
    "LicenceStatus",
    "ProcessingStatus",
]
