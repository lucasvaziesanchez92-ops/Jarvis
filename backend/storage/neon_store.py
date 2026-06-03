"""PostgreSQL/NeonDB-based persistence layer using SQLAlchemy."""
import os
from typing import Any, List

from sqlalchemy import create_engine, Column, String, Text, DateTime, Boolean, Integer, func, ForeignKey, Index
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy.sql import text

from backend.storage.models import Base, NoteModel, TodoModel, ThreadModel, MessageModel


class PostgresStore:
    """PostgreSQL/NeonDB-based storage using SQLAlchemy with connection pooling."""

    def __init__(self, database_url: str | None = None):
        if database_url is None:
            from backend.config import settings
            database_url = getattr(settings, 'database_url', None)

        if database_url is None:
            raise ValueError("database_url is required for PostgresStore")

        self.engine = create_engine(
            database_url,
            echo=False,
            poolclass=QueuePool,
            pool_size=10,
            max_overflow=20,
            pool_timeout=30,
            pool_recycle=3600,
            connect_args={
                "connect_timeout": 15,
            },
        )

        Base.metadata.create_all(self.engine)

        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
        )

    def get_session(self) -> Session:
        return self.SessionLocal()

    def close(self):
        self.engine.dispose()

    def soft_delete(self, model_class, record_id: str) -> bool:
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


_store: PostgresStore | None = None


def get_store() -> PostgresStore:
    global _store
    if _store is None:
        _store = PostgresStore()
    return _store


def reset_store():
    global _store
    if _store:
        _store.close()
    _store = None


def create_store(database_url: str) -> PostgresStore:
    global _store
    if _store:
        _store.close()
    _store = PostgresStore(database_url)
    return _store