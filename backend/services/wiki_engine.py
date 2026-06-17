"""Wiki Engine — ChromaDB indexing + RAG retrieval for Obsidian vault."""
import os
os.environ['HF_HOME'] = os.path.join(os.getcwd(), 'data', 'hf_cache')
os.environ['XDG_CACHE_HOME'] = os.path.join(os.getcwd(), 'data', 'xdg_cache')
import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import chromadb
import frontmatter
from loguru import logger

# ── Config ──────────────────────────────────────────────────────
VAULT_PATH = os.getenv("OBSIDIAN_VAULT_PATH", os.path.join("backend", "data", "brain"))
CHROMA_PATH = os.getenv("CHROMA_DB_PATH", "data/chroma_wiki")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100

_client: Optional[chromadb.PersistentClient] = None
_collection: Optional[chromadb.Collection] = None


def _get_client() -> chromadb.PersistentClient:
    global _client
    if _client is None:
        Path(CHROMA_PATH).mkdir(parents=True, exist_ok=True)
        import chromadb.config
        settings = chromadb.config.Settings(
            anonymized_telemetry=False,
            allow_reset=True,
            is_persistent=True,
        )
        _client = chromadb.PersistentClient(path=str(CHROMA_PATH), settings=settings)
    return _client


def _get_collection() -> chromadb.Collection:
    global _collection
    if _collection is None:
        client = _get_client()
        _collection = client.get_or_create_collection(
            name="obsidian_notes",
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


# ── Chunking ─────────────────────────────────────────────────────
def _split_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks for embedding."""
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
        i += chunk_size - overlap
    return chunks


def _extract_links(text: str) -> list[str]:
    return re.findall(r'\[\[([^\]]+)\]\]', text)


def _extract_tags(fm: frontmatter.Post) -> list[str]:
    tags = fm.get("tags", [])
    if isinstance(tags, str):
        return [tags]
    if isinstance(tags, list):
        return [t if isinstance(t, str) else str(t) for t in tags]
    return []


# ── Indexing ─────────────────────────────────────────────────────
def index_vault(vault_path: str = VAULT_PATH) -> dict:
    """Index all markdown files from the database into ChromaDB."""
    from backend.storage import get_store
    from backend.storage.models import NoteModel

    store = get_store()
    session = store.get_session()
    
    try:
        notes = session.query(NoteModel).filter(NoteModel.deleted_at.is_(None)).all()
    except Exception as e:
        logger.error(f"Error querying database for index_vault: {e}")
        return {"error": str(e), "pages": 0}
    finally:
        session.close()

    if not notes:
        return {"pages": 0, "message": "No markdown notes found in database"}

    collection = _get_collection()

    try:
        existing_ids = collection.get()["ids"]
        if existing_ids:
            collection.delete(ids=existing_ids)
    except Exception as e:
        logger.warning(f"Could not clear wiki collection: {e}")

    ids, documents, metadatas = [], [], []
    indexed_chunks = 0

    for note in notes:
        try:
            raw = note.content
            # Still parse frontmatter if it exists in the content
            post = frontmatter.loads(raw)
            content = post.content if post.content else raw
            title = note.title
            tags = _extract_tags(post)
            links = _extract_links(content)
            created = note.created_at.isoformat() if note.created_at else datetime.now(timezone.utc).isoformat()
        except Exception as e:
            logger.warning(f"Error parsing note {note.id}: {e}")
            continue

        chunks = _split_text(content)
        if not chunks:
            chunks = [content] if content else ["(empty)"]

        for i, chunk in enumerate(chunks):
            chunk_id = hashlib.md5(f"{note.id}_{i}".encode()).hexdigest()
            ids.append(chunk_id)
            documents.append(chunk)
            metadatas.append({
                "filepath": str(note.title) + ".md",
                "filename": str(note.title) + ".md",
                "title": str(title),
                "tags": ", ".join(str(t) for t in tags),
                "links": ", ".join(str(l) for l in links),
                "created": str(created),
                "chunk_index": str(i),
                "chunk_total": str(len(chunks)),
            })
            indexed_chunks += 1

    batch_size = 100
    for j in range(0, len(ids), batch_size):
        end = min(j + batch_size, len(ids))
        collection.add(
            ids=ids[j:end],
            documents=documents[j:end],
            metadatas=metadatas[j:end],
        )

    logger.info(f"Wiki indexed: {len(notes)} files, {indexed_chunks} chunks")
    return {
        "pages": len(notes),
        "chunks": indexed_chunks,
        "vault": vault_path,
        "last_indexed": datetime.now(timezone.utc).isoformat(),
    }


# ── Search ───────────────────────────────────────────────────────
def search_vault(query: str, n_results: int = 5) -> list[dict]:
    """Semantic search over the wiki vault."""
    collection = _get_collection()
    try:
        results = collection.query(query_texts=[query], n_results=n_results)
    except Exception as e:
        logger.warning(f"Wiki search failed: {e}")
        # Try to re-index if collection is empty
        stats = get_stats()
        if stats["chunks"] == 0:
            index_vault()
            results = collection.query(query_texts=[query], n_results=n_results)
        else:
            return []

    output = []
    if not results["ids"] or not results["ids"][0]:
        return []

    for i in range(len(results["ids"][0])):
        meta = results["metadatas"][0][i] if results["metadatas"] and results["metadatas"][0] else {}
        output.append({
            "id": results["ids"][0][i],
            "content": results["documents"][0][i] if results["documents"] else "",
            "title": meta.get("title", ""),
            "filename": meta.get("filename", ""),
            "filepath": meta.get("filepath", ""),
            "tags": meta.get("tags", ""),
            "links": meta.get("links", ""),
            "score": round(results["distances"][0][i], 4) if results.get("distances") and results["distances"][0] else 0,
        })
    return output


def get_stats() -> dict:
    """Get indexing statistics."""
    collection = _get_collection()
    count = collection.count()
    return {"chunks": count, "vault": VAULT_PATH, "embedding_model": EMBEDDING_MODEL}


# ── Watchdog (live file changes) ─────────────────────────────────
import time
import threading

_stop_watchdog = threading.Event()
_watchdog_thread: Optional[threading.Thread] = None
_debounce_timer: Optional[threading.Timer] = None


def start_watchdog(vault_path: str = VAULT_PATH):
    """Start monitoring the vault for file changes and auto-reindex (debounced)."""
    global _watchdog_thread

    def _rebuild():
        global _debounce_timer
        logger.info("Wiki change detected, reindexing...")
        try:
            index_vault(vault_path)
        except Exception as e:
            logger.error(f"Reindex failed: {e}")
        _debounce_timer = None

    if _watchdog_thread is not None:
        return

    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
    except ImportError:
        logger.warning("watchdog not installed — live reindex disabled")
        return

    class VaultHandler(FileSystemEventHandler):
        def _schedule_reindex(self):
            global _debounce_timer
            if _debounce_timer is not None:
                _debounce_timer.cancel()
            _debounce_timer = threading.Timer(3.0, _rebuild)
            _debounce_timer.daemon = True
            _debounce_timer.start()

        def on_modified(self, event):
            if event.src_path.endswith(".md") and not event.is_directory:
                self._schedule_reindex()

        def on_created(self, event):
            self._schedule_reindex()

        def on_deleted(self, event):
            self._schedule_reindex()

    vault = Path(vault_path)
    if not vault.exists():
        logger.warning(f"Vault path does not exist for watchdog: {vault_path}")
        return

    observer = Observer()
    observer.schedule(VaultHandler(), str(vault), recursive=True)
    observer.daemon = True

    def run():
        _stop_watchdog.clear()
        observer.start()
        logger.info(f"Wiki watchdog started: {vault_path}")
        while not _stop_watchdog.is_set():
            time.sleep(5)
        observer.stop()
        observer.join()
        logger.info("Wiki watchdog stopped")

    _watchdog_thread = threading.Thread(target=run, daemon=True)
    _watchdog_thread.start()


def stop_watchdog():
    _stop_watchdog.set()
