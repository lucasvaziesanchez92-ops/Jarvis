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
    from backend.storage import get_store
    from backend.storage.models import NoteModel

    store = get_store()
    session = store.get_session()
    files = []
    try:
        try:
            notes = session.query(NoteModel).filter(NoteModel.deleted_at.is_(None)).all()
        except Exception:
            session.rollback()
            notes = session.query(NoteModel).all()
            
        for note in notes:
            # Solo incluir notas que parecen archivos wiki (que tienen un directorio en el título)
            if note.title and "/" in note.title:
                files.append({
                    "name": note.title.split("/")[-1] + ".md",
                    "path": note.title + ".md",
                    "directory": note.title.split("/")[0]
                })
            else:
                title_val = note.title if note.title else "Untitled"
                files.append({
                    "name": title_val + ".md",
                    "path": title_val + ".md",
                    "directory": "brain"
                })
    finally:
        session.close()
    return {"files": files}

@router.get("/file")
async def get_file(path: str = Query(..., description="Relative path to the file")):
    from backend.storage import get_store
    from backend.storage.models import NoteModel

    # Remove .md if present to match the title
    title = path.replace(".md", "")
    store = get_store()
    session = store.get_session()
    try:
        note = session.query(NoteModel).filter_by(title=title, deleted_at=None).first()
        if not note:
            raise HTTPException(404, "File not found")
        content = note.content
    finally:
        session.close()
    return {"path": path, "content": content}

@router.get("/graph")
async def get_graph():
    from backend.storage import get_store
    from backend.storage.models import NoteModel, GraphNodeModel, GraphEdgeModel
    import frontmatter

    store = get_store()
    session = store.get_session()
    nodes = []
    links = []
    node_ids = set()
    
    try:
        # 1. Fetch Markdown Notes (Traditional Wiki Nodes)
        notes = session.query(NoteModel).filter(NoteModel.deleted_at.is_(None)).all()
        for note in notes:
            node_id = note.title
            try:
                post = frontmatter.loads(note.content)
                content = post.content if post.content else note.content
                tags = post.get("tags", [])
                summary = post.get("summary", "")
                if isinstance(tags, str): tags = [tags]
            except Exception:
                content = note.content
                tags = []
                summary = ""

            nodes.append({
                "id": node_id, 
                "group": "brain",
                "tags": tags,
                "summary": summary
            })
            node_ids.add(node_id)
            
            matches = re.findall(r"\[\[(.*?)\]\]", content)
            for target in matches:
                target_id = target.split("|")[0].strip()
                links.append({"source": node_id, "target": target_id, "label": "referencia"})

        # 2. Fetch Structured Graph Nodes
        graph_nodes = session.query(GraphNodeModel).all()
        for gn in graph_nodes:
            if gn.id not in node_ids:
                nodes.append({
                    "id": gn.id,
                    "group": gn.type.lower() if gn.type else "concept",
                    "tags": [gn.type] if gn.type else [],
                    "summary": gn.description or ""
                })
                node_ids.add(gn.id)

        # 3. Fetch Structured Graph Edges
        graph_edges = session.query(GraphEdgeModel).all()
        for ge in graph_edges:
            links.append({
                "source": ge.source_id,
                "target": ge.target_id,
                "label": ge.relation
            })

    except Exception as e:
        import traceback
        traceback.print_exc()
        pass
    finally:
        session.close()

    # Filtramos links que apuntan a nodos que no existen
    valid_links = []
    for link in links:
        if link["source"] in node_ids and link["target"] in node_ids:
            valid_links.append(link)

    return {"nodes": nodes, "links": valid_links}
