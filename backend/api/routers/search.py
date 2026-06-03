"""Unified search endpoint — search across notes, todos, calendar, emails + semantic RAG."""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from backend.storage.sqlite_store import get_store
from sqlalchemy import or_

router = APIRouter(prefix="/search", tags=["search"])


class SemanticSearchResult(BaseModel):
    type: str
    title: str
    content: str
    score: float
    note_id: str | None = None
    page_name: str | None = None


class SemanticSearchResponse(BaseModel):
    query: str
    results: list[SemanticSearchResult]
    total: int


class SearchResult(BaseModel):
    """A single search result."""
    type: str  # "note", "todo", "calendar_event", "email"
    id: str
    title: str
    content: str
    metadata: dict = {}


class SearchResponse(BaseModel):
    """Unified search response."""
    query: str
    results: list[SearchResult]
    total: int


@router.get("", response_model=SearchResponse)
@router.get("/", response_model=SearchResponse)
async def unified_search(
    q: str = Query(..., min_length=1, description="Search query"),
    types: str = Query(
        default="all",
        description="Comma-separated types to search: notes,todos,calendar,emails or 'all'",
    ),
    limit: int = Query(default=20, ge=1, le=100),
    store=Depends(get_store),
):
    """
    Unified search across all data sources.

    Searches notes, todos, calendar events, and emails with a single query.
    """
    query_lower = q.lower()
    results: list[SearchResult] = []
    type_list = types.split(",") if types != "all" else ["notes", "todos", "calendar", "emails"]

    session = store.get_session()

    try:
        # Search Notes
        if "notes" in type_list:
            from backend.storage.sqlite_store import NoteModel
            notes = session.query(NoteModel).filter(
                or_(
                    NoteModel.title.ilike(f"%{q}%"),
                    NoteModel.content.ilike(f"%{q}%"),
                    NoteModel.tags.ilike(f"%{q}%"),
                )
            ).limit(limit).all()

            for note in notes:
                results.append(SearchResult(
                    type="note",
                    id=note.id,
                    title=note.title,
                    content=note.content[:200],
                    metadata={"tags": note.tags, "created_at": str(note.created_at)},
                ))

        # Search Todos
        if "todos" in type_list:
            from backend.storage.sqlite_store import TodoModel
            todos = session.query(TodoModel).filter(
                TodoModel.text.ilike(f"%{q}%")
            ).limit(limit).all()

            for todo in todos:
                results.append(SearchResult(
                    type="todo",
                    id=todo.id,
                    title=todo.text,
                    content=f"Priority: {todo.priority}, Completed: {todo.completed}",
                    metadata={
                        "priority": todo.priority,
                        "completed": todo.completed,
                        "due_date": str(todo.due_date) if todo.due_date else None,
                    },
                ))

        # Search Threads (as proxy for messages)
        if "emails" in type_list:
            from backend.storage.sqlite_store import ThreadModel, MessageModel
            threads = session.query(ThreadModel).filter(
                ThreadModel.title.ilike(f"%{q}%")
            ).limit(limit).all()

            for thread in threads:
                results.append(SearchResult(
                    type="thread",
                    id=thread.id,
                    title=thread.title or "Untitled",
                    content=thread.meta[:200] if thread.meta else "",
                    metadata={"status": thread.status, "created_at": str(thread.created_at)},
                ))

        # Calendar & Email searches require Google API — skip if not configured
        # These would be searched via their respective services in production

    finally:
        session.close()

    return SearchResponse(
        query=q,
        results=results[:limit],
        total=len(results),
    )


@router.get("/semantic", response_model=SemanticSearchResponse)
async def semantic_search_endpoint(
    q: str = Query(..., min_length=1, description="Semantic search query"),
    source: str = Query(
        default="all",
        description="Source filter: 'notes', 'wiki', or 'all'",
    ),
    top_k: int = Query(default=5, ge=1, le=20),
):
    """
    Semantic search using ChromaDB vector embeddings.
    Searches notes and wiki using natural language queries.
    """
    try:
        from backend.service.vector_service import semantic_search
        source_filter = source if source in ("notes", "wiki") else None
        raw_results = semantic_search(q, top_k=top_k, source_filter=source_filter)
    except ImportError:
        raw_results = []

    results = [
        SemanticSearchResult(
            type=r.get("source", "unknown"),
            title=r.get("title", "Unknown"),
            content=r.get("content", ""),
            score=r.get("score", 0.0),
            note_id=r.get("note_id"),
            page_name=r.get("page_name"),
        )
        for r in raw_results
    ]

    return SemanticSearchResponse(
        query=q,
        results=results,
        total=len(results),
    )


@router.get("/stats")
async def knowledge_stats():
    """Get statistics about the semantic knowledge index."""
    try:
        from backend.service.vector_service import get_index_stats
        return get_index_stats()
    except ImportError:
        return {"status": "unavailable", "reason": "ChromaDB not installed"}
