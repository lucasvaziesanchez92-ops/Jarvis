"""RAG retrieval node — busca contexto en wiki+notas con gate inteligente."""
from backend.agent.state import JarvisState

try:
    from backend.service.vector_service import semantic_search
except ImportError:
    semantic_search = None

_TRIVIAL = {"hola", "chau", "gracias", "dale", "ok", "si", "no", "bien", "bueno", "buenas", "gracias!", "perfecto"}
_TRIGGERS = ("qué", "quien", "cómo", "cuándo", "dónde", "por qué", "cuál", "?"
             "explica", "describe", "investiga", "busca", "recorda", "recuerdo",
             "sabes", "conoces", "tenés", "tienes", "wiki", "nota", "proyecto")


def _should_retrieve(query: str) -> bool:
    q = query.lower().strip().rstrip("?!.")
    if len(q) < 10 or q in _TRIVIAL:
        return False
    return any(t in q for t in _TRIGGERS)


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

    try:
        results = semantic_search(last_msg, top_k=3, source_filter=None)
    except Exception:
        return {"retrieved_context": []}

    if not results:
        return {"retrieved_context": []}

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

    full = "\n---\n".join(parts) if parts else ""
    return {"retrieved_context": [full] if full else []}
