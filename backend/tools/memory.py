"""LangChain tools for agent memory management."""
from langchain_core.tools import tool

from backend.services.memory_service import memory_service


@tool
def search_memory(query: str, category: str = "") -> str:
    """Search long-term memory for relevant facts and past experiences.
    Use this when you need to recall information the user has shared before.
    """
    results = memory_service.search_memories(
        query,
        category=category or None,
        limit=5,
    )
    if not results:
        return "No tengo recuerdos relevantes sobre eso."
    lines = [f"- {r['fact']} (confianza: {r['confidence']:.0%})" for r in results]
    return "Recuerdos relevantes:\n" + "\n".join(lines)


@tool
def save_memory(fact: str, category: str = "general") -> str:
    """Save an important fact, preference, or rule to long-term memory.
    Use this when the user shares something important you should remember for later.
    """
    memory_id = memory_service.save_fact(fact, category)
    return f"Recuerdo guardado: '{fact}' (ID: {memory_id})"


@tool
def list_memories(category: str = "") -> str:
    """List memory categories or recent memories.
    Use this when the user asks 'what do you remember' or 'show my memories'.
    """
    if category:
        results = memory_service.search_memories("", category=category, limit=20)
        if not results:
            return f"No hay recuerdos en la categoría '{category}'."
        lines = [f"- {r['fact']}" for r in results]
        return f"Recuerdos en '{category}':\n" + "\n".join(lines)
    categories = memory_service.list_categories()
    if not categories:
        return "No hay recuerdos guardados aún."
    lines = [f"- {c['category']}: {c['count']} recuerdos" for c in categories]
    return "Categorías de memoria:\n" + "\n".join(lines)


@tool
def delete_memory(memory_id: str) -> str:
    """Delete a specific memory by ID. Use when the user asks to forget something."""
    success = memory_service.delete_memory(memory_id)
    if success:
        return f"Recuerdo {memory_id} eliminado."
    return f"Recuerdo {memory_id} no encontrado."


@tool
def compact_memory() -> str:
    """Clean up and compact long-term memory, removing old and unused memories.
    Use this when the user asks to 'clean memory', 'optimize memory', or 'ccleaner'.
    """
    result = memory_service.compact_memories()
    return (
        f"Memoria compactada: {result['before']} → {result['after']} recuerdos. "
        f"Se eliminaron {result['removed']} recuerdos obsoletos."
    )


@tool
def diagnose_agent() -> str:
    """Run a full diagnostic of the agent's health, memory, and tool usage.
    Use this when the user asks 'how are you', 'diagnose', 'status report', or 'health check'.
    """
    report = memory_service.run_diagnose()
    health = report["health"]
    mem = report["memory"]

    lines = [
        f"📊 Diagnóstico del Agente:",
        f"",
        f"🧠 Memoria:",
        f"  - Long-term: {mem['long_term_count']} recuerdos",
        f"  - Episódica: {mem['episodic_count']} experiencias",
        f"  - Categorías: {', '.join(f'{k}({v})' for k, v in mem['categories'].items()) or 'ninguna'}",
        f"  - Tamaño: {mem['total_size_kb']} KB",
        f"",
        f"⚙️ Estado:",
        f"  - Ejecuciones totales: {report['diagnostics']['total_runs']}",
        f"  - Errores recientes: {len(report['diagnostics']['recent_errors'])}",
        f"  - Última limpieza: {report['diagnostics']['last_cleanup'] or 'nunca'}",
        f"",
        f"🔧 Herramientas más usadas:",
    ]
    for tool_name, count in sorted(
        report.get("tool_usage", {}).items(), key=lambda x: x[1], reverse=True
    )[:5]:
        lines.append(f"  - {tool_name}: {count} veces")

    lines.append("")
    if all(health.values()):
        lines.append("✅ Todo está saludable.")
    else:
        issues = [k for k, v in health.items() if not v]
        lines.append(f"⚠️ Problemas detectados: {', '.join(issues)}")

    return "\n".join(lines)


@tool
def cleanup_agent() -> str:
    """Run a full CCleaner-style cleanup: compact memory, clear old errors, optimize state.
    Use this when the user asks to 'run ccleaner', 'full cleanup', or 'optimize everything'.
    """
    result = memory_service.run_cleanup()
    mem = result["memory_compaction"]
    return (
        f"🧹 Limpieza completa:\n"
        f"  - Memoria: {mem['before']} → {mem['after']} recuerdos ({mem['removed']} eliminados)\n"
        f"  - Errores antiguos: limpiados\n"
        f"  - Estado: optimizado ✅"
    )
