"""Wiki tools — Obsidian-powered knowledge base with ChromaDB semantic search."""
from langchain_core.tools import tool
from pathlib import Path
import os


@tool
def wiki_query(query: str) -> str:
    """Busca en tu segundo cerebro (Obsidian) usando búsqueda semántica con ChromaDB."""
    try:
        from backend.services.wiki_engine import search_vault
        results = search_vault(query, n_results=5)
        if not results:
            return "No encontré información relevante en tu segundo cerebro sobre eso."
        lines = []
        for r in results:
            score_pct = round((1 - r.get("score", 1.0)) * 100, 1) if r.get("score") else 0
            lines.append(f"**{r.get('title', 'Nota')}** ({score_pct}% match)\n{r.get('content', '')[:300]}")
        return "\n\n".join(lines)
    except Exception as e:
        return f"Error buscando en el wiki: {e}. Probá indexar con /api/v1/wiki/reindex."


@tool
def wiki_save_research(title: str, content: str) -> str:
    """Guarda investigación en la wiki. Crea un archivo .md y reindexa."""
    data_dir = Path(os.getenv("DATA_DIR", "data"))
    sources_dir = data_dir / "sources"
    sources_dir.mkdir(parents=True, exist_ok=True)

    safe_title = "".join(c for c in title if c.isalnum() or c in " _-").strip().replace(" ", "_")
    source_path = sources_dir / f"{safe_title}.md"
    source_path.write_text(f"# {title}\n\n{content}", encoding="utf-8")

    try:
        from backend.services.wiki_engine import index_vault
        index_vault()
    except Exception:
        pass

    return f"Conocimiento '{title}' guardado en tu segundo cerebro."


@tool
def wiki_ingest(file_name: str) -> str:
    """Procesa un archivo .md existente y lo integra en la wiki."""
    data_dir = Path(os.getenv("DATA_DIR", "data"))
    source_path = data_dir / "sources" / file_name
    if not source_path.exists():
        return f"Error: No se encontró {file_name} en data/sources/."
    try:
        from backend.services.wiki_engine import index_vault
        index_vault()
    except Exception:
        pass
    return f"Archivo {file_name} integrado en tu wiki."


@tool
def shopping_list_add(item: str, category: str = "general") -> str:
    """Agrega un item a la lista de compras. Se guarda como nota taggeada."""
    from backend.tools.notes import create_note
    return create_note.invoke({"title": f"Comprar: {item}", "content": f"Item: {item}\nCategoría: {category}", "tags": ["shopping", category]})


@tool
def shopping_list_view() -> str:
    """Ver items en la lista de compras."""
    from backend.tools.notes import list_notes
    return list_notes.invoke({"tag": "shopping"})
