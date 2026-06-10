"""LangGraph nodes — single agent with native bind_tools.
minimax-m2.7:cloud soporta function calling via OpenAI-compatible API."""
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool
from loguru import logger

from backend.agent.state import JarvisState
from backend.agent.personalities import get_persona
from backend.config import settings
from backend.core.resilience import llm_breaker


def _get_persona_prompt(persona: str) -> str:
    return get_persona(persona).system_prompt


def _trim_messages(messages: list, persona: str = "profesional"):
    max_messages = getattr(settings, "max_context_messages", 30)
    if len(messages) <= max_messages:
        return messages
    system_msg = [m for m in messages if isinstance(m, SystemMessage)]
    other = [m for m in messages if not isinstance(m, SystemMessage)]
    keep = max_messages - len(system_msg)
    return system_msg + other[-keep:]


def call_model_with_tools(
    state: JarvisState, llm_with_tools, extra_context: str = "",
) -> dict:
    """Invoke LLM with bound tools + RAG context.

    If bind_tools call fails (model too slow, prompt too big, etc.),
    fall back to a plain LLM call without tool descriptions.
    """
    persona = state.get("persona", "profesional")
    base = list(state["messages"])

    # Inject tool-usage contract: the LLM must not hallucinate results.
    # If a tool was actually executed, its ToolMessage will appear in the
    # conversation. Otherwise, the LLM must explicitly say so.
    tool_contract = (
        "REGLAS CRITICAS SOBRE HERRAMIENTAS (NO IGNORAR, SON ABSOLUTAS):\n"
        "1. NUNCA digas 'no dispongo de herramienta', 'no tengo acceso', o 'no puedo'. Si la herramienta esta en tu lista, la tenes. Usala.\n"
        "2. Solo di 'no puedo' cuando el ToolMessage retorno un error especifico (ej: 'error 403', 'credenciales faltantes'). NUNCA lo digas por iniciativa propia.\n"
        "3. MAPA COMPLETO DE HERRAMIENTAS DISPONIBLES:\n"
        "   - Notas: create_note, list_notes, get_note, update_note, delete_note\n"
        "   - Tareas: create_todo, list_todos, complete_todo, update_todo, delete_todo\n"
        "   - Memoria: search_memory, save_memory, list_memories, delete_memory\n"
        "   - Wiki: wiki_query, wiki_save_research, wiki_ingest\n"
        "   - Web: web_search\n"
        "   - Tiempo: get_current_time, get_current_date\n"
        "   - Gmail (Google): list_gmail, search_gmail, send_gmail, get_gmail_detail, delete_gmail_message, trash_gmail_message\n"
        "   - Drive (Google): search_drive, list_drive_files, list_drive_folder, read_drive_file, get_drive_file_info, upload_drive_file, delete_drive_file, analyze_drive_image\n"
        "   - Calendar (Google): list_calendar_google, create_calendar_event_google\n"
        "   - Calendar (CRUD): list_calendar_events, create_calendar_event, update_calendar_event, delete_calendar_event\n"
        "   - Storage (Railway): list_storage_files, read_storage_file, delete_storage_file\n"
        "4. Despues de CADA tool_call, el sistema te va a dar un ToolMessage con el resultado. Si NO lo viste, no digas que ya lo hiciste.\n"
        "5. Si la herramienta devuelve error, reporta el error EXACTO al usuario. NO finjas exito.\n"
        "6. NUNCA inventes resultados. Si el ToolMessage dice 'error 403', eso es lo que reportas.\n"
        "7. Si NO ves una herramienta en tu lista (porque no se cargo o no se incluyo), podes decir 'esa funcion no esta disponible en este momento'. Pero si SI la ves, usala sin dudar."
    )

    if extra_context and base:
        ctx = HumanMessage(content=(
            "[INFORMACIÓN RELEVANTE DE TU MEMORIA EXTERNA]\n" + extra_context
        ))
        enriched = base[:-1] + [ctx, base[-1]]
    else:
        enriched = base

    system = SystemMessage(content=_get_persona_prompt(persona) + "\n\n" + tool_contract)
    messages = [system] + enriched
    trimmed = _trim_messages(messages, persona)

    try:
        response = llm_breaker.call(llm_with_tools.invoke, trimmed)
    except Exception as e:
        err_msg = str(e)
        logger.warning(f"bind_tools falló ({type(e).__name__}: {err_msg[:150]}) — usando invoke plano")
        from backend.llm import get_llm
        llm = get_llm()
        try:
            response = llm_breaker.call(llm.invoke, trimmed)
        except Exception as e2:
            logger.error(f"plain LLM también falló: {e2}")
            response = AIMessage(content=(
                "Tuve un problema de latencia con mi modelo. "
                "¿Podés reformular la pregunta o intentar de nuevo en unos segundos?"
            ))

    return {"messages": [response]}
