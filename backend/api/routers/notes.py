"""REST endpoints for Notes."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.models.note import Note
from backend.services import notes_service

router = APIRouter()


class NoteCreate(BaseModel):
    title: str
    content: str
    tags: list[str] = []


class NoteUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    tags: list[str] | None = None


@router.get("", response_model=list[Note])
def list_notes(tag: str | None = None):
    return notes_service.list_notes(tag)


@router.post("", response_model=Note, status_code=201)
def create_note(body: NoteCreate):
    return notes_service.create_note(body.title, body.content, body.tags)


@router.get("/{note_id}", response_model=Note)
def get_note(note_id: str):
    data = notes_service.get_note(note_id)
    if not data:
        raise HTTPException(status_code=404, detail="Note not found")
    return data


@router.put("/{note_id}", response_model=Note)
def update_note(note_id: str, body: NoteUpdate):
    data = notes_service.update_note(note_id, body.title, body.content, body.tags)
    if not data:
        raise HTTPException(status_code=404, detail="Note not found")
    return data


@router.delete("/{note_id}", status_code=204)
def delete_note(note_id: str):
    result = notes_service.delete_note(note_id)
    if "not found" in result:
        raise HTTPException(status_code=404, detail="Note not found")


class ObsidianMigrateRequest(BaseModel):
    vault_path: str


class ObsidianMigrateResponse(BaseModel):
    found: int
    migrated: int
    skipped: int
    errors: list[str]


@router.post("/import/obsidian", response_model=ObsidianMigrateResponse)
def import_obsidian(body: ObsidianMigrateRequest):
    from backend.scripts.migrate_obsidian_notes import migrate_notes
    result = migrate_notes(body.vault_path)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result
