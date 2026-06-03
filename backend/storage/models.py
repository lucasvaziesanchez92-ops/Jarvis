"""Unified storage models for both SQLite and PostgreSQL/NeonDB.

These models are used by the storage layer and services.
The correct model set is selected at runtime based on STORAGE_TYPE.
"""
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Column, String, Text, DateTime, Boolean, Index
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class NoteModel(Base):
    __tablename__ = "notes"
    __table_args__ = {"extend_existing": True}

    id = Column(String, primary_key=True)
    title = Column(String, nullable=False, index=True)
    content = Column(Text, nullable=False)
    tags = Column(Text, default="[]")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    deleted_at = Column(DateTime, nullable=True, default=None, index=True)


class TodoModel(Base):
    __tablename__ = "todos"
    __table_args__ = {"extend_existing": True}

    id = Column(String, primary_key=True)
    text = Column(Text, nullable=False, index=True)
    completed = Column(Boolean, default=False, index=True)
    priority = Column(String, default="medium", index=True)
    due_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    deleted_at = Column(DateTime, nullable=True, default=None, index=True)


class ThreadModel(Base):
    __tablename__ = "threads"
    __table_args__ = {"extend_existing": True}

    id = Column(String, primary_key=True)
    title = Column(String, nullable=True, index=True)
    status = Column(String, default="active")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    meta = Column(Text, nullable=True)
    deleted_at = Column(DateTime, nullable=True, default=None, index=True)


class MessageModel(Base):
    __tablename__ = "messages"
    __table_args__ = {"extend_existing": True}

    id = Column(String, primary_key=True)
    thread_id = Column(String, nullable=False, index=True)
    role = Column(String, default="user")
    content = Column(Text, nullable=False)
    meta = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    __table_args__ = (
        Index('ix_messages_thread_created', 'thread_id', 'created_at'),
    )