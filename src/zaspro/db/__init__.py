"""Database layer: typed SQLAlchemy 2.x models, engine, session factory.

The schema is designed whole (SPEC §5) but created in migration batches per
phase. M1 batch: curriculum (`subjects`, `units`, `topics`,
`topic_prerequisites`) and `sources`.
"""

from zaspro.db.base import Base, get_engine, session_scope

__all__ = ["Base", "get_engine", "session_scope"]
