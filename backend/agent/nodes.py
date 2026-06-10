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
    #
    # ABSOLUTE RULES — violating any of these is a hallucination that
    # erodes user trust. These come directly from the user saying
    # 'JARVIS miente sobre lo que puede hacer, no sirve para nada'.
    tool_contract = (
        "REGLAS INQUEBRANTABLES — VIOLAR CUALQUIERA ES ALUCINAR:\n"
        "\n"
        "REGLA 1: NUNCA digas 'no dispongo de herramienta', 'no tengo acceso', 'no puedo', 'esa funcion no esta disponible' "
        "a menos que el ToolMessage que recibiste CONTENGA TEXTUALMENTE un error tipo 'no implementado', 'not implemented', 'RuntimeError: ...'. "
        "Si el ToolMessage dice 'Error al subir', 'error 403', 'no encontrado', etc., REPORTALO TEXTUALMENTE, no inventes un resultado. "
        "Si NO recibiste ToolMessage (el usuario no te pidio ejecutar nada especifico), entonces no digas nada sobre herramientas.\n"
        "\n"
        "REGLA 2: MAPA COMPLETO Y VERIFICADO DE HERRAMIENTAS DISPONIBLES EN TU ESQUEMA:\n"
        "   - Notas: create_note, list_notes, get_note, update_note, delete_note\n"
        "   - Tareas: create_todo, list_todos, complete_todo, update_todo, delete_todo\n"
        "   - Memoria: search_memory, save_memory, list_memories, delete_memory\n"
        "   - Wiki: wiki_query, wiki_save_research, wiki_ingest\n"
        "   - Web: web_search\n"
        "   - Tiempo: get_current_time, get_current_date\n"
        "   - Gmail (Google, OAuth): list_gmail, search_gmail, send_gmail, get_gmail_detail, delete_gmail_message, trash_gmail_message\n"
        "   - Drive (Google, OAuth): search_drive, list_drive_files, list_drive_folder, read_drive_file, get_drive_file_info, upload_drive_file, delete_drive_file, analyze_drive_image\n"
        "   - Calendar (Google, OAuth): list_calendar_google, create_calendar_event_google\n"
        "   - Calendar (CRUD local): list_calendar_events, create_calendar_event, update_calendar_event, delete_calendar_event\n"
        "   - Storage (Railway): list_storage_files, read_storage_file, delete_storage_file\n"
        "\n"
        "REGLA 3: Despues de CADA tool_call, el sistema te va a dar un ToolMessage con el resultado. Si NO lo viste todavia, "
        "no digas 'ya lo hice' ni 'listo'. Esperá el ToolMessage.\n"
        "\n"
        "REGLA 4: Si la herramienta devuelve ERROR (sea 403, RuntimeError, etc.), REPORTA EL ERROR EXACTO. NO finjas exito. "
        "Si te conectaste a Google pero read_drive_file da 403, eso significa que el archivo es un Google Doc y necesita export — "
        "exportalo a texto usando la tool correcta. NO digas 'no puedo', DECI 'lo exporto a texto plano'.\n"
        "\n"
        "REGLA 5: Si la tool NO esta en tu lista, podes decir 'esa funcion no esta disponible'. Pero si SI la ves en la lista, usala. "
        "No asumas — verifica mirando tu lista de tools.\n"
        "\n"
        "REGLA 6: Cuando uses una tool, EMITI el tool_call en tu respuesta interna. NO describas el resultado en texto hasta "
        "haber visto el ToolMessage correspondiente.\n"
        "\n"
        "REGLA 7: Si el ToolMessage tiene contenido util (datos de Drive, lista de correos, etc.), USALO directamente en tu respuesta al usuario. "
        "Si el ToolMessage dice 'No hay archivos', DECI 'No hay archivos'. Si dice '3 correos encontrados', LISTA los 3 correos. "
        "NO alucines contenido que no recibiste.\n"
        "\n"
        "REGLA 8: NUNCA ejecutes la misma tool_call dos veces en la misma respuesta. Si ya ejecutaste list_gmail, no la ejecutes de nuevo. "
        "Una tool_call por accion. En paralelo si son independientes."
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
