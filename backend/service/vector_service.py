"""Vector store service using ChromaDB for semantic search over notes and wiki."""
import os
import threading
from pathlib import Path
from typing import Optional

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from backend.config import settings

CHROMA_DIR = os.path.join(os.getenv("DATA_DIR", "data"), "chroma_db")
COLLECTION_NOTES = "jarvis_notes"
COLLECTION_WIKI = "jarvis_wiki"

_embedding_model = None
_chroma_client = None
_lock = threading.Lock()


def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True}
        )
    return _embedding_model


def get_chroma_client(persist_directory: str = CHROMA_DIR) -> Chroma:
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = Chroma(
            persist_directory=persist_directory,
            embedding_function=get_embedding_model()
        )
    return _chroma_client


def _get_text_splitter(chunk_size: int = 500, chunk_overlap: int = 50):
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n## ", "\n# ", "\n\n", "\n", ". ", " "]
    )


def index_note(note_id: str, title: str, content: str, tags: list[str] | None = None) -> str:
    """Index a note in the vector store. Creates or updates."""
    chroma = get_chroma_client()
    splitter = _get_text_splitter()

    full_text = f"# {title}\n\n{content}"
    if tags:
        full_text += f"\n\nTags: {', '.join(tags)}"

    metadata = {
        "note_id": note_id,
        "title": title,
        "tags": tags or [],
        "source": "notes"
    }

    existing = chroma.get(where={"note_id": note_id}, include=[])
    if existing and existing.get("ids"):
        chroma.delete(ids=existing["ids"])

    chunks = splitter.split_text(full_text)
    documents = [
        Document(page_content=chunk, metadata={**metadata, "chunk_index": i})
        for i, chunk in enumerate(chunks)
    ]

    with _lock:
        chroma.add_documents(documents)

    return f"Indexed {len(chunks)} chunks for note '{title}'"


def delete_note_from_index(note_id: str) -> str:
    """Remove a note from the vector index."""
    chroma = get_chroma_client()
    with _lock:
        existing = chroma.get(where={"note_id": note_id}, include=[])
        if existing and existing.get("ids"):
            chroma.delete(ids=existing["ids"])
            return f"Deleted {len(existing['ids'])} chunks for note {note_id}"
    return f"No chunks found for note {note_id}"


def index_wiki_page(page_name: str, content: str, source_file: str = "") -> str:
    """Index a wiki page in the vector store."""
    chroma = get_chroma_client()
    splitter = _get_text_splitter()

    full_text = f"# {page_name}\n\n{content}"

    metadata = {
        "page_name": page_name,
        "source": "wiki",
        "source_file": source_file
    }

    existing = chroma.get(where={"page_name": page_name, "source": "wiki"}, include=[])
    if existing and existing.get("ids"):
        chroma.delete(ids=existing["ids"])

    chunks = splitter.split_text(full_text)
    documents = [
        Document(page_content=chunk, metadata={**metadata, "chunk_index": i})
        for i, chunk in enumerate(chunks)
    ]

    with _lock:
        chroma.add_documents(documents)

    return f"Indexed {len(chunks)} chunks for wiki page '{page_name}'"


def semantic_search(query: str, top_k: int = 5, source_filter: str | None = None) -> list[dict]:
    """
    Perform semantic search across indexed content.
    Returns list of dicts with: content, title, score, metadata.
    """
    chroma = get_chroma_client()

    where_filter = None
    if source_filter:
        where_filter = {"source": source_filter}

    results = chroma.similarity_search_with_score(
        query,
        k=top_k,
        filter=where_filter if where_filter else None
    )

    output = []
    for doc, score in results:
        output.append({
            "content": doc.page_content,
            "title": doc.metadata.get("title") or doc.metadata.get("page_name", "Unknown"),
            "score": float(score),
            "source": doc.metadata.get("source", "unknown"),
            "note_id": doc.metadata.get("note_id"),
            "page_name": doc.metadata.get("page_name"),
            "tags": doc.metadata.get("tags", [])
        })

    return output


def semantic_search_wiki(query: str, top_k: int = 5) -> list[dict]:
    """Search only in wiki pages."""
    return semantic_search(query, top_k=top_k, source_filter="wiki")


def semantic_search_notes(query: str, top_k: int = 5) -> list[dict]:
    """Search only in user notes."""
    return semantic_search(query, top_k=top_k, source_filter="notes")


def reindex_all_notes(notes: list[dict]) -> str:
    """Reindex all notes. Use sparingly - for migrations only."""
    chroma = get_chroma_client()
    with _lock:
        try:
            chroma.delete(where={"source": "notes"})
        except Exception:
            pass

    total_chunks = 0
    for note in notes:
        result = index_note(
            note_id=note["id"],
            title=note["title"],
            content=note["content"],
            tags=note.get("tags")
        )
        chunks = int(result.split()[1])
        total_chunks += chunks

    return f"Reindexed {len(notes)} notes ({total_chunks} total chunks)"


def reindex_all_wiki(pages: list[dict]) -> str:
    """Reindex all wiki pages. Use sparingly - for migrations only."""
    chroma = get_chroma_client()
    with _lock:
        try:
            chroma.delete(where={"source": "wiki"})
        except Exception:
            pass

    total_chunks = 0
    for page in pages:
        result = index_wiki_page(
            page_name=page["page_name"],
            content=page["content"],
            source_file=page.get("source_file", "")
        )
        chunks = int(result.split()[1])
        total_chunks += chunks

    return f"Reindexed {len(pages)} wiki pages ({total_chunks} total chunks)"


def get_index_stats() -> dict:
    """Get statistics about the vector index."""
    chroma = get_chroma_client()
    try:
        notes_count = len(chroma.get(where={"source": "notes"}, include=[]) or [])
        wiki_count = len(chroma.get(where={"source": "wiki"}, include=[]) or [])
        return {
            "notes_chunks": notes_count,
            "wiki_chunks": wiki_count,
            "total": notes_count + wiki_count,
            "embedding_model": "sentence-transformers/all-MiniLM-L6-v2"
        }
    except Exception as e:
        return {"error": str(e)}
