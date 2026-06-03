"""Business logic for thread management."""
import json
from datetime import datetime, timezone
from typing import Literal, List, Optional

from sqlalchemy.orm import Session

from backend.models.thread import Thread
from backend.storage.sqlite_store import get_store, ThreadModel


def create_thread(title: str | None = None, metadata: dict | None = None) -> dict:
    """Create a new thread."""
    store = get_store()
    session: Session = store.get_session()
    try:
        thread = Thread(
            title=title,
            metadata=metadata,
        )
        thread_model = ThreadModel(
            id=thread.id,
            title=thread.title,
            status=thread.status,
            created_at=thread.created_at,
            updated_at=thread.updated_at,
            meta=json.dumps(metadata) if metadata else None,
        )
        session.add(thread_model)
        session.commit()
        return thread.model_dump()
    finally:
        session.close()


def get_thread(thread_id: str) -> dict | None:
    """Get a thread by ID."""
    store = get_store()
    session: Session = store.get_session()
    try:
        thread_model = session.query(ThreadModel).filter(ThreadModel.id == thread_id).first()
        if not thread_model:
            return None
        thread = Thread(
            id=thread_model.id,
            title=thread_model.title,
            status=thread_model.status,
            created_at=thread_model.created_at,
            updated_at=thread_model.updated_at,
            metadata=json.loads(thread_model.meta) if thread_model.meta else None,
        )
        return thread.model_dump()
    finally:
        session.close()


def list_threads(status: Literal["active", "archived", "deleted"] | None = None) -> List[dict]:
    """List all threads, optionally filtered by status."""
    store = get_store()
    session: Session = store.get_session()
    try:
        query = session.query(ThreadModel)
        if status:
            query = query.filter(ThreadModel.status == status)
        thread_models = query.all()
        threads = []
        for tm in thread_models:
            thread = Thread(
                id=tm.id,
                title=tm.title,
                status=tm.status,
                created_at=tm.created_at,
                updated_at=tm.updated_at,
                metadata=json.loads(tm.meta) if tm.meta else None,
            )
            threads.append(thread.model_dump())
        return threads
    finally:
        session.close()


def update_thread_status(thread_id: str, status: Literal["active", "archived", "deleted"]) -> dict | None:
    """Update thread status."""
    store = get_store()
    session: Session = store.get_session()
    try:
        thread_model = session.query(ThreadModel).filter(ThreadModel.id == thread_id).first()
        if not thread_model:
            return None
        thread_model.status = status
        thread_model.updated_at = datetime.now(timezone.utc)
        session.commit()
        # Return updated thread
        thread = Thread(
            id=thread_model.id,
            title=thread_model.title,
            status=thread_model.status,
            created_at=thread_model.created_at,
            updated_at=thread_model.updated_at,
            metadata=json.loads(thread_model.meta) if thread_model.meta else None,
        )
        return thread.model_dump()
    finally:
        session.close()


def archive_thread(thread_id: str) -> dict | None:
    """Archive a thread."""
    return update_thread_status(thread_id, "archived")


def delete_thread(thread_id: str) -> str:
    """Delete a thread."""
    store = get_store()
    session: Session = store.get_session()
    try:
        thread_model = session.query(ThreadModel).filter(ThreadModel.id == thread_id).first()
        if not thread_model:
            return f"Thread {thread_id} not found."
        session.delete(thread_model)
        session.commit()
        return f"Thread {thread_id} deleted."
    finally:
        session.close()
