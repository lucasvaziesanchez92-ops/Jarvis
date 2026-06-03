"""Business logic for message management."""
import json
from typing import List, Optional, Any

from sqlalchemy.orm import Session

from backend.models.message import Message
from backend.storage.sqlite_store import get_store, MessageModel


def create_message(
    thread_id: str,
    role: str = "user",
    content: str = "",
    metadata: dict[str, Any] | None = None,
) -> dict:
    """Create a new message in a thread."""
    store = get_store()
    session: Session = store.get_session()
    try:
        message = Message(
            thread_id=thread_id,
            role=role,
            content=content,
            metadata=metadata,
        )
        message_model = MessageModel(
            id=message.id,
            thread_id=message.thread_id,
            role=message.role,
            content=message.content,
            meta=json.dumps(metadata) if metadata else None,
            created_at=message.created_at,
        )
        session.add(message_model)
        session.commit()
        return message.model_dump()
    finally:
        session.close()


def get_message(message_id: str) -> dict | None:
    """Get a message by ID."""
    store = get_store()
    session: Session = store.get_session()
    try:
        message_model = session.query(MessageModel).filter(MessageModel.id == message_id).first()
        if not message_model:
            return None
        message = Message(
            id=message_model.id,
            thread_id=message_model.thread_id,
            role=message_model.role,
            content=message_model.content,
            metadata=json.loads(message_model.meta) if message_model.meta else None,
            created_at=message_model.created_at,
        )
        return message.model_dump()
    finally:
        session.close()


def list_messages(thread_id: str, limit: int | None = None) -> List[dict]:
    """List all messages in a thread, ordered by creation time."""
    store = get_store()
    session: Session = store.get_session()
    try:
        query = (
            session.query(MessageModel)
            .filter(MessageModel.thread_id == thread_id)
            .order_by(MessageModel.created_at.asc())
        )
        if limit:
            query = query.limit(limit)
        message_models = query.all()
        messages = []
        for mm in message_models:
            message = Message(
                id=mm.id,
                thread_id=mm.thread_id,
                role=mm.role,
                content=mm.content,
                metadata=json.loads(mm.meta) if mm.meta else None,
                created_at=mm.created_at,
            )
            messages.append(message.model_dump())
        return messages
    finally:
        session.close()


def delete_message(message_id: str) -> str:
    """Delete a message."""
    store = get_store()
    session: Session = store.get_session()
    try:
        message_model = session.query(MessageModel).filter(MessageModel.id == message_id).first()
        if not message_model:
            return f"Message {message_id} not found."
        session.delete(message_model)
        session.commit()
        return f"Message {message_id} deleted."
    finally:
        session.close()


def delete_thread_messages(thread_id: str) -> str:
    """Delete all messages in a thread."""
    store = get_store()
    session: Session = store.get_session()
    try:
        session.query(MessageModel).filter(MessageModel.thread_id == thread_id).delete()
        session.commit()
        return f"All messages in thread {thread_id} deleted."
    finally:
        session.close()
