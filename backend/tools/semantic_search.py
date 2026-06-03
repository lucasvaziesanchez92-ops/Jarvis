"""Semantic search tools for the Jarvis agent — RAG over notes and wiki."""
from langchain_core.tools import tool

from backend.service.vector_service import (
    semantic_search_notes,
    semantic_search_wiki,
    semantic_search,
    get_index_stats
)


@tool
def search_notes_semantic(query: str, top_k: int = 5) -> str:
    """
    Búsqueda semántica en tus notas personales.
    Úsala cuando no recuerdes exactamente el título de una nota pero sí el contenido.
    Devuelve las notas más relevantes con puntuación de similitud.
    """
    results = semantic_search_notes(query, top_k=top_k)

    if not results:
        return f"No encontré notas relevantes para '{query}'. Probá con otros términos."

    output = [f"## Resultados para '{query}' ({len(results)} encontrados)\n"]
    for i, r in enumerate(results, 1):
        similarity_pct = round((1 - r["score"]) * 100, 1)
        output.append(
            f"\n### {i}. {r['title']} (similitud: {similarity_pct}%)\n"
            f"{r['content'][:300]}{'...' if len(r['content']) > 300 else ''}\n"
        )
        if r.get("tags"):
            output.append(f"Tags: {', '.join(r['tags'])}\n")

    return "\n".join(output)


@tool
def search_wiki_semantic(query: str, top_k: int = 5) -> str:
    """
    Búsqueda semántica en tu wiki/conocimiento guardado.
    Úsala para buscar conceptos, ideas o investigaciones que guardaste.
    Devuelve páginas wiki relevantes con puntuación de similitud.
    """
    results = semantic_search_wiki(query, top_k=top_k)

    if not results:
        return f"No encontré contenido en la wiki para '{query}'. Probá con otros términos."

    output = [f"## Wiki: Resultados para '{query}' ({len(results)} encontrados)\n"]
    for i, r in enumerate(results, 1):
        similarity_pct = round((1 - r["score"]) * 100, 1)
        output.append(
            f"\n### {i}. {r['title']} (similitud: {similarity_pct}%)\n"
            f"{r['content'][:400]}{'...' if len(r['content']) > 400 else ''}\n"
        )

    return "\n".join(output)


@tool
def search_all_knowledge(query: str, top_k: int = 5) -> str:
    """
    Búsqueda semántica global en TODO tu conocimiento: notas personales Y wiki.
    Esta es la herramienta principal cuando querés buscar en tu 'segundo cerebro'.
    """
    results = semantic_search(query, top_k=top_k)

    if not results:
        return f"No encontré nada en tu conocimiento para '{query}'. Ni en notas ni en wiki."

    by_source = {"notes": [], "wiki": []}
    for r in results:
        src = r.get("source", "unknown")
        if src in by_source:
            by_source[src].append(r)
        else:
            by_source["notes"].append(r)

    output = [f"## Búsqueda Global: '{query}' ({len(results)} resultados)\n"]

    if by_source["notes"]:
        output.append("\n### 📝 NOTAS PERSONALES\n")
        for i, r in enumerate(by_source["notes"], 1):
            similarity_pct = round((1 - r["score"]) * 100, 1)
            output.append(
                f"{i}. **{r['title']}** (similitud: {similarity_pct}%)\n"
                f"   {r['content'][:200]}{'...' if len(r['content']) > 200 else ''}\n"
            )

    if by_source["wiki"]:
        output.append("\n### 🧠 WIKI / CONOCIMIENTO\n")
        for i, r in enumerate(by_source["wiki"], len(by_source["notes"]) + 1):
            similarity_pct = round((1 - r["score"]) * 100, 1)
            output.append(
                f"{i}. **{r['title']}** (similitud: {similarity_pct}%)\n"
                f"   {r['content'][:200]}{'...' if len(r['content']) > 200 else ''}\n"
            )

    return "\n".join(output)


@tool
def get_knowledge_stats() -> str:
    """
    Muestra estadísticas del índice de conocimiento vectorial.
    Útil para saber cuántas notas y páginas wiki están indexadas.
    """
    stats = get_index_stats()

    if "error" in stats:
        return f"Error obteniendo estadísticas: {stats['error']}"

    return (
        "## 📊 Estado del Índice de Conocimiento\n\n"
        f"- **Notas indexadas:** {stats.get('notes_chunks', 0)} chunks\n"
        f"- **Wiki indexada:** {stats.get('wiki_chunks', 0)} chunks\n"
        f"- **Total:** {stats.get('total', 0)} chunks\n"
        f"- **Modelo de embeddings:** {stats.get('embedding_model', 'N/A')}\n"
    )
