"""Business logic for note management."""
import json
import logging
from datetime import datetime, timezone
from typing import List

from sqlalchemy.orm import Session

from backend.models.note import Note
from backend.storage.sqlite_store import get_store, NoteModel

logger = logging.getLogger(__name__)


def _sync_to_vector(note_id: str, title: str, content: str, tags: List[str] | None = None):
    """Sync note to vector store. Non-blocking if Chroma fails."""
    try:
        from backend.service.vector_service import index_note
        index_note(note_id=note_id, title=title, content=content, tags=tags)
    except Exception as e:
        logger.warning(f"Vector sync failed for note {note_id}: {e}")


def create_note(title: str, content: str, tags: List[str] | None = None) -> dict:
    store = get_store()
    session: Session = store.get_session()
    try:
        note = Note(title=title, content=content, tags=tags or [])
        note_model = NoteModel(
            id=note.id,
            title=note.title,
            content=note.content,
            tags=json.dumps(note.tags),
            created_at=note.created_at,
            updated_at=note.updated_at
        )
        session.add(note_model)
        session.commit()
        result = note.model_dump()
        session.close()
        _sync_to_vector(note_id=result["id"], title=result["title"], content=result["content"], tags=result["tags"])
        return result
    finally:
        session.close()


def list_notes(tag: str | None = None) -> List[dict]:
    store = get_store()
    session: Session = store.get_session()
    try:
        query = session.query(NoteModel)
        if tag:
            # Filter notes that contain the tag in their tags list
            notes_models = query.all()
            filtered_notes = []
            for nm in notes_models:
                tags_list = json.loads(nm.tags)
                if tag in tags_list:
                    filtered_notes.append(nm)
            notes_models = filtered_notes
        else:
            notes_models = query.all()
        notes = []
        for nm in notes_models:
            note = Note(
                id=nm.id,
                title=nm.title,
                content=nm.content,
                tags=json.loads(nm.tags),
                created_at=nm.created_at,
                updated_at=nm.updated_at
            )
            notes.append(note.model_dump())
        return notes
    finally:
        session.close()


def get_note(note_id: str) -> dict | None:
    store = get_store()
    session: Session = store.get_session()
    try:
        note_model = session.query(NoteModel).filter(NoteModel.id == note_id).first()
        if not note_model:
            return None
        note = Note(
            id=note_model.id,
            title=note_model.title,
            content=note_model.content,
            tags=json.loads(note_model.tags),
            created_at=note_model.created_at,
            updated_at=note_model.updated_at
        )
        return note.model_dump()
    finally:
        session.close()


def update_note(note_id: str, title: str | None = None, content: str | None = None, tags: List[str] | None = None) -> dict | None:
    store = get_store()
    session: Session = store.get_session()
    try:
        note_model = session.query(NoteModel).filter(NoteModel.id == note_id).first()
        if not note_model:
            return None
        if title is not None:
            note_model.title = title
        if content is not None:
            note_model.content = content
        if tags is not None:
            note_model.tags = json.dumps(tags)
        note_model.updated_at = datetime.now(timezone.utc)
        session.commit()
        note = Note(
            id=note_model.id,
            title=note_model.title,
            content=note_model.content,
            tags=json.loads(note_model.tags),
            created_at=note_model.created_at,
            updated_at=note_model.updated_at
        )
        result = note.model_dump()
        session.close()
        _sync_to_vector(note_id=result["id"], title=result["title"], content=result["content"], tags=result["tags"])
        return result
    finally:
        session.close()


def delete_note(note_id: str) -> str:
    try:
        from backend.service.vector_service import delete_note_from_index
        delete_note_from_index(note_id)
    except Exception as e:
        logger.warning(f"Vector delete sync failed for note {note_id}: {e}")
    store = get_store()
    session: Session = store.get_session()
    try:
        note_model = session.query(NoteModel).filter(NoteModel.id == note_id).first()
        if not note_model:
            return f"Note {note_id} not found."
        session.delete(note_model)
        session.commit()
        return f"Note {note_id} deleted."
    finally:
        session.close()
