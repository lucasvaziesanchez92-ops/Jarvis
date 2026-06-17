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
    """Guarda información explícitamente en la Wiki para recordarlo permanentemente."""
    from backend.storage import get_store
    from backend.storage.models import NoteModel
    import uuid
    import datetime

    store = get_store()
    session = store.get_session()
    
    try:
        title = "".join(c for c in title if c.isalnum() or c in " _-").strip()
        final_content = f"---\ntitle: {title}\ntags: [raw]\n---\n\n{content}"
        
        existing = session.query(NoteModel).filter_by(title=title, deleted_at=None).first()
        if existing:
            existing.content += "\n\n" + content
        else:
            new_note = NoteModel(
                id=str(uuid.uuid4()),
                title=title,
                content=final_content
            )
            session.add(new_note)
        session.commit()
        return f"Registro '{title}' guardado permanentemente en la Wiki base de datos."
    except Exception as e:
        session.rollback()
        return f"Error guardando en la Wiki: {e}"
    finally:
        session.close()


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
