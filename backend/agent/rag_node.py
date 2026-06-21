"""RAG retrieval node — busca contexto en wiki+notas con gate inteligente."""
from backend.agent.state import JarvisState

try:
    from backend.services.wiki_engine import search_vault as semantic_search
except ImportError:
    semantic_search = None

_TRIVIAL = {"hola", "chau", "gracias", "dale", "ok", "si", "no", "bien", "bueno", "buenas", "gracias!", "perfecto"}

def _should_retrieve(query: str) -> bool:
    q = query.lower().strip().rstrip("?!.")
    if len(q) < 5 or q in _TRIVIAL:
        return False
    return True


def _build_context_string(results: list[dict], source_label: str) -> str:
    if not results:
        return ""
    lines = [f"\n## {source_label}\n"]
    seen = set()
    for r in results:
        title = r.get("title", "Unknown")
        if title in seen:
            continue
        seen.add(title)
        pct = round((1 - r.get("score", 1.0)) * 100, 1)
        lines.append(f"**{title}** ({pct}% match)\n{r.get('content', '')[:400]}")
    return "\n".join(lines)


def retrieval_node(state: JarvisState) -> dict:
    if semantic_search is None:
        return {"retrieved_context": []}

    last_msg = state["messages"][-1].content if state["messages"] else ""
    if not last_msg.strip() or not _should_retrieve(last_msg):
        return {"retrieved_context": []}

    results = []
    try:
        results = semantic_search(last_msg, n_results=3)
    except Exception:
        pass

    by_source: dict = {"notes": [], "wiki": []}
    for r in results:
        src = r.get("source", "notes")
        by_source.setdefault(src, []).append(r)

    parts = []
    if by_source.get("notes"):
        short = by_source["notes"][:2]
        parts.append(_build_context_string(short, "TUS NOTAS"))
    if by_source.get("wiki"):
        short = by_source["wiki"][:2]
        parts.append(_build_context_string(short, "SEGUNDO CEREBRO"))

    try:
        from backend.services.graph_engine import search_graph
        graph_context = search_graph(last_msg)
        if graph_context:
            parts.append(graph_context)
    except Exception as e:
        import traceback
        import logging
        logging.getLogger(__name__).error(f"Error fetching graph context: {e}")
        pass

    try:
        from backend.services.todos_service import list_todos
        active_todos = list_todos(show_completed=False)
        if active_todos:
            lines = ["\n## TAREAS PENDIENTES\n"]
            for t in active_todos[:5]:
                due = f" (Vence: {t.get('due_date')})" if t.get('due_date') else ""
                lines.append(f"- [{t.get('priority', 'medium')}] {t.get('text')}{due}")
            parts.append("\n".join(lines))
    except Exception:
        pass

    try:
        from backend.services.calendar_service import list_events
        upcoming = list_events(max_results=3)
        if upcoming:
            lines = ["\n## PRÓXIMOS EVENTOS (CALENDARIO)\n"]
            for e in upcoming:
                lines.append(f"- {e.get('start')} -> {e.get('end')} | {e.get('summary')}")
            parts.append("\n".join(lines))
    except Exception:
        pass

    full = "\n---\n".join(parts) if parts else ""
    return {"retrieved_context": [full] if full else []}
