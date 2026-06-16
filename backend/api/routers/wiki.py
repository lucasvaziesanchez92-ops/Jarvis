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

import os
import re

@router.get("/files")
async def get_files():
    vault_path = get_stats()["vault"]
    files = []
    if not os.path.exists(vault_path):
        return {"files": []}
    for root, _, filenames in os.walk(vault_path):
        for name in filenames:
            if name.endswith(".md"):
                full_path = os.path.join(root, name)
                rel_path = os.path.relpath(full_path, vault_path)
                files.append({
                    "name": name,
                    "path": rel_path.replace("\\", "/"),
                    "directory": os.path.basename(root)
                })
    return {"files": files}

@router.get("/file")
async def get_file(path: str = Query(..., description="Relative path to the file")):
    vault_path = get_stats()["vault"]
    full_path = os.path.abspath(os.path.join(vault_path, path))
    if not full_path.startswith(os.path.abspath(vault_path)):
        raise HTTPException(400, "Invalid path")
    if not os.path.exists(full_path):
        raise HTTPException(404, "File not found")
    with open(full_path, "r", encoding="utf-8") as f:
        content = f.read()
    return {"path": path, "content": content}

@router.get("/graph")
async def get_graph():
    vault_path = get_stats()["vault"]
    nodes = []
    links = []
    node_ids = set()
    
    if not os.path.exists(vault_path):
        return {"nodes": [], "links": []}

    for root, _, filenames in os.walk(vault_path):
        for name in filenames:
            if name.endswith(".md"):
                node_id = name.replace(".md", "")
                nodes.append({"id": node_id, "group": os.path.basename(root)})
                node_ids.add(node_id)
                
    for root, _, filenames in os.walk(vault_path):
        for name in filenames:
            if name.endswith(".md"):
                node_id = name.replace(".md", "")
                full_path = os.path.join(root, name)
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # Find all [[Links]]
                matches = re.findall(r"\[\[(.*?)\]\]", content)
                for target in matches:
                    # Clean up targets (e.g. handle aliases like [[Real Note|Alias]])
                    target_id = target.split("|")[0].strip()
                    links.append({"source": node_id, "target": target_id})
                    if target_id not in node_ids:
                        nodes.append({"id": target_id, "group": "ghost"})
                        node_ids.add(target_id)
                        
    return {"nodes": nodes, "links": links}

