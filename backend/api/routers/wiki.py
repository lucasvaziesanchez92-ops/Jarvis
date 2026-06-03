"""Wiki API router — search and manage the Obsidian second brain."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from backend.services.wiki_engine import search_vault, index_vault, get_stats, start_watchdog

router = APIRouter(prefix="/wiki", tags=["wiki"])

class ReindexResponse(BaseModel):
    pages: int
    chunks: int
    vault: str
    last_indexed: str
    message: str = ""

class SearchResponse(BaseModel):
    query: str
    results: list[dict]
    total: int

@router.get("/search")
async def search(
    q: str = Query(..., description="Search query"),
    n: int = Query(5, ge=1, le=20, description="Number of results"),
):
    results = search_vault(q, n_results=n)
    return {"query": q, "results": results, "total": len(results)}


@router.post("/reindex")
async def reindex():
    result = index_vault()
    if "error" in result:
        raise HTTPException(400, detail=result["error"])
    return result


@router.get("/health")
async def health():
    stats = get_stats()
    return {
        "service": "wiki",
        "configured": stats["chunks"] > 0,
        "chunks": stats["chunks"],
        "vault": stats["vault"],
        "embedding_model": stats["embedding_model"],
    }


@router.post("/watch")
async def watch():
    """Start the file watcher for auto-reindex."""
    start_watchdog()
    return {"status": "watching", "vault": "active"}
