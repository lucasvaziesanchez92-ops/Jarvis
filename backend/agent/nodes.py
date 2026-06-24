"""LangGraph nodes — single agent with native bind_tools.
minimax-m2.7:cloud soporta function calling via OpenAI-compatible API."""
import traceback
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

    # Keep message order: NEVER orphan a ToolMessage. If the last
    # kept message is a ToolMessage (role='tool'), we must also keep
    # the AIMessage that produced its tool_call_id, otherwise the
    # LLM sees 'tool' after 'user' and rejects with 400.
    keep = max_messages - len(system_msg)
    trimmed_other = other[-keep:]
    
    # NEW FIX: Remove any orphaned ToolMessage at the VERY BEGINNING of the kept window.
    # A ToolMessage MUST follow an AIMessage with tool_calls. If it's the first message, it's orphaned.
    while trimmed_other and isinstance(trimmed_other[0], ToolMessage):
        trimmed_other = trimmed_other[1:]

    if trimmed_other and isinstance(trimmed_other[-1], ToolMessage):
        # Find the AIMessage with matching tool_call_id in the
        # already-kept or discarded window. Walk backwards through
        # the original 'other' list.
        target_id = trimmed_other[-1].tool_call_id
        for j in range(len(other) - len(trimmed_other), -1, -1):
            cand = other[j]
            if isinstance(cand, AIMessage) and getattr(cand, "tool_calls", None):
                ids = {tc.get("id") for tc in cand.tool_calls}
                if target_id in ids:
                    # Insert this AIMessage right before the
                    # ToolMessage and re-trim.
                    before = trimmed_other[:-1]
                    after = trimmed_other[-1]
                    if cand in before:
                        idx = before.index(cand)
                        trimmed_other = before + [after]
                    else:
                        # Need to evict an older message to make room
                        trimmed_other = before + [cand, after]
                    # Still might be over budget; drop the very
                    # oldest non-essential message.
                    while len(system_msg) + len(trimmed_other) > max_messages and len(trimmed_other) > 2:
                        trimmed_other = trimmed_other[1:]
                    break
    return system_msg + trimmed_other


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
        "REGLA 7: Si el ToolMessage devuelve datos (lista de correos, eventos, clima, contenido de archivo), ¡TIENES QUE IMPRIMIRLOS TODOS! "
        "NUNCA resumas la respuesta diciendo 'Encontré correos, ¿quieres que los lea?'. ¡LÉELOS DE INMEDIATO! "
        "Tu trabajo es DAR la información directamente al usuario, no preguntarle si la quiere. "
        "Si dice '3 correos encontrados', LISTA EXACTAMENTE cuáles son. NO alucines contenido que no recibiste.\n"
        "\n"
        "REGLA 8: NUNCA ejecutes la misma tool_call dos veces en la misma respuesta. Si ya ejecutaste list_gmail, no la ejecutes de nuevo. "
        "Una tool_call por accion. En paralelo si son independientes.\n"
        "\n"
        "REGLA 9: SIEMPRE utiliza 'wiki_query' o 'search_memory' de forma proactiva al inicio de la conversación si el usuario menciona proyectos pasados, ideas, o hace preguntas que requieran contexto previo. Demuestra que conectas la información a largo plazo.\n"
        "\n"
        "REGLA 10: TIENES CAPACIDADES EN EL MUNDO REAL. SÍ PUEDES enviar correos reales, crear eventos, etc. Si el usuario te pide enviar un correo, usa la herramienta `send_gmail` INMEDIATAMENTE. NUNCA digas que no puedes enviar correos o realizar acciones en el mundo real."
    )

    # If the last message is a ToolMessage (role='tool'), we cannot
    # put a HumanMessage or another user-role message after it.
    # That would produce the OpenAI error 'Unexpected role tool
    # after role user' (caught with devstral-small-2:24b on
    # 2026-06-10). Inject the RAG context as a SystemMessage suffix
    # in that case, or drop the extra context.
    last_is_tool = bool(base) and isinstance(base[-1], ToolMessage)

    if extra_context and base and not last_is_tool:
        # Prevent context limit exceeded errors (llama-3.1-8b has 8k limit)
        if len(extra_context) > 6000:
            extra_context = extra_context[:6000] + "\n\n...[CONTEXTO TRUNCADO POR TAMAÑO]..."
            
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
        logger.error(f"bind_tools falló en agent_node: {type(e).__name__}: {err_msg[:500]}")
        logger.error(traceback.format_exc()[:1500])
        from backend.llm import get_llm
        llm = get_llm()
        try:
            response = llm_breaker.call(llm.invoke, trimmed)
        except Exception as e2:
            logger.error(f"plain LLM también falló: {type(e2).__name__}: {e2}")
            import traceback as tb
            logger.error(tb.format_exc()[:1500])
            response = AIMessage(content=(
                f"Error crítico de red o de memoria del modelo. Detalle: {type(e2).__name__}: {str(e2)[:200]}"
            ))

    # FALLBACK PARSER: If Llama-3.1 outputs raw tags instead of native tool calls
    if isinstance(response, AIMessage) and not getattr(response, "tool_calls", None) and response.content:
        import re
        import json
        import uuid
        matches = re.finditer(r'<function=([^>]+)>(.*?)</function>', response.content, re.DOTALL)
        tool_calls = []
        for match in matches:
            name = match.group(1).strip()
            args_str = match.group(2).strip()
            try:
                args = json.loads(args_str) if args_str else {}
            except json.JSONDecodeError:
                args = {}
            tool_calls.append({
                "name": name,
                "args": args,
                "id": f"call_{uuid.uuid4().hex[:10]}"
            })
        if tool_calls:
            response.tool_calls = tool_calls

    return {"messages": [response]}
