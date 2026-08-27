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
from zaspro.db.models.exercises import (
    Exercise,
    ExerciseFigure,
    ExerciseOrigin,
    VerificationStatus,
)
from zaspro.db.models.ingestion import (
    ContentType,
    ExtractionMethod,
    ExtractionStatus,
    Figure,
    RenderStatus,
    SourceChunk,
    SourceDocument,
    SourceFormat,
)
from zaspro.db.models.jobs import Job, JobStatus, JobType
from zaspro.db.models.mapping import (
    ChunkMapping,
    MappingStatus,
    ReviewDecision,
    ReviewDecisionType,
    ReviewItem,
    ReviewItemType,
    ReviewReasonCode,
    ReviewStatus,
)
from zaspro.db.models.sources import (
    LicenceStatus,
    ProcessingStatus,
    Source,
    SourceType,
)

__all__ = [
    # curriculum
    "Subject", "Unit", "Topic", "TopicPrerequisite",
    "TopicLevel", "TopicStatus", "PrerequisiteImportance",
    # sources / ingestion
    "Source", "SourceType", "LicenceStatus", "ProcessingStatus",
    "SourceDocument", "SourceChunk", "Figure",
    "ExtractionStatus", "ContentType", "ExtractionMethod",
    "SourceFormat", "RenderStatus",
    # exercises
    "Exercise", "ExerciseFigure", "ExerciseOrigin", "VerificationStatus",
    # jobs
    "Job", "JobType", "JobStatus",
    # mapping + review
    "ChunkMapping", "MappingStatus",
    "ReviewItem", "ReviewItemType", "ReviewStatus",
    "ReviewDecision", "ReviewDecisionType", "ReviewReasonCode",
]
