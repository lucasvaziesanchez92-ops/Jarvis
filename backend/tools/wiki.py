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
            return (
                "Tu segundo cerebro está vacío o no hay notas relevantes para esa consulta. "
            )
        lines = []
        for r in results:
            score_pct = round((1 - r.get("score", 1.0)) * 100, 1) if r.get("score") else 0
            lines.append(f"**{r.get('title', 'Nota')}** (Match semántico: {score_pct}%)\n{r.get('content', '')[:500]}")
        return "\n\n".join(lines)
    except Exception as e:
        return f"Error al consultar la wiki: {e}"


@tool
def wiki_capture(title: str, content: str) -> str:
    """Guarda un texto crudo o recorte en la carpeta _raw/ para su posterior procesamiento cognitivo."""
    from backend.services.wiki_engine import get_stats
    vault_path = get_stats()["vault"]
    raw_dir = Path(vault_path) / "_raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    safe_title = "".join(c for c in title if c.isalnum() or c in " _-").strip().replace(" ", "_")
    source_path = raw_dir / f"{safe_title}.md"
    source_path.write_text(f"---\ntitle: {title}\ntags: [raw]\n---\n\n{content}", encoding="utf-8")

    return f"Conocimiento crudo '{title}' capturado en la carpeta _raw de tu segundo cerebro. El extractor lo procesará después."


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
