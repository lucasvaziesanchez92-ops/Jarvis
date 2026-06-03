"""SQLite-based persistence layer using SQLAlchemy with connection pooling and soft deletes."""
import os
from pathlib import Path
from typing import Any, List

from sqlalchemy import create_engine, Column, String, Text, DateTime, Boolean, Integer, func
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy.sql import text

from backend.config import settings
from backend.storage.models import Base, NoteModel, TodoModel, ThreadModel, MessageModel


class SqliteStore:
    """SQLite-based storage using SQLAlchemy with connection pooling."""

    def __init__(self, db_path: str | None = None):
        if db_path is None:
            data_dir = Path(settings.data_dir)
            data_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(data_dir / "jarvis.db")

        # Connection pool configuration
        self.engine = create_engine(
            f"sqlite:///{db_path}",
            echo=False,
            poolclass=QueuePool,
            pool_size=10,  # Max persistent connections
            max_overflow=20,  # Extra connections under load
            pool_timeout=30,  # Seconds to wait for connection
            pool_recycle=3600,  # Recycle connections after 1 hour
            connect_args={"check_same_thread": False},  # Required for SQLite
        )

        # Create tables if they don't exist
        Base.metadata.create_all(self.engine)

        # Session factory with autocommit=False, autoflush=False
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
        )

    def get_session(self) -> Session:
        """Get a new database session. Caller must close it."""
        return self.SessionLocal()

    def close(self):
        """Dispose of the engine and all connections."""
        self.engine.dispose()

    # ── Soft Delete Helpers ──────────────────────────────────

    def soft_delete(self, model_class, record_id: str) -> bool:
        """Soft delete a record by setting deleted_at timestamp."""
        session = self.get_session()
        try:
            record = session.query(model_class).filter(
                model_class.id == record_id,
                model_class.deleted_at.is_(None),
            ).first()

            if record:
                record.deleted_at = func.now()
                session.commit()
                return True
            return False
        except Exception:
            session.rollback()
            return False
        finally:
            session.close()

    def get_active(self, model_class, filters=None, order_by=None, limit=None):
        """Query only active (non-deleted) records."""
        session = self.get_session()
        try:
            query = session.query(model_class).filter(model_class.deleted_at.is_(None))

            if filters:
                query = query.filter(*filters)

            if order_by:
                query = query.order_by(order_by)

            if limit:
                query = query.limit(limit)

            return query.all()
        finally:
            session.close()


# Global store instance with connection pooling
_store: SqliteStore | None = None


def get_store() -> SqliteStore:
    """Get or create the global SqliteStore instance."""
    global _store
    if _store is None:
        _store = SqliteStore()
    return _store


def reset_store():
    """Reset the store singleton (useful for tests)."""
    global _store
    if _store:
        _store.close()
    _store = None