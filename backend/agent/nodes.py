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

    # ── Build the system prompt (persona + tool list) ──────────────
    from datetime import datetime, timezone
    current_time = datetime.now(timezone.utc).strftime("%A, %d %B %Y - %H:%M:%S")
    tool_list = (
        "HORA SERVIDOR: " + current_time + " UTC (usuario en GMT-6, resta 6h).\n"
        "TOOLS REALES: create_note,list_notes,get_note,update_note,delete_note | "
        "create_todo,list_todos,complete_todo,update_todo,delete_todo | "
        "wiki_query,wiki_capture | get_current_time,get_current_date | "
        "calculate_math,get_weather | "
        "search_memory,save_memory,list_memories,delete_memory,compact_memory,diagnose_agent | "
        "web_search,buscar_imagenes_web,buscar_reversa_gratis | "
        "list_gmail,search_gmail,send_gmail,get_gmail_detail,delete_gmail_message,trash_gmail_message | "
        "search_drive,list_drive_files,list_drive_folder,read_drive_file,get_drive_file_info,upload_drive_file,delete_drive_file,analyze_drive_image | "
        "list_calendar_google,create_calendar_event_google,list_calendar_events,create_calendar_event,update_calendar_event,delete_calendar_event | "
        "list_storage_files,read_storage_file,delete_storage_file"
    )
    system = SystemMessage(content=_get_persona_prompt(persona) + "\n\n" + tool_list)

    # ── Inject behavior rules as a HumanMessage right before the LAST user message ──
    # Rules placed here (close to the request) are obeyed. Rules in the system prompt are ignored.
    behavior_rules = (
        "[REGLAS DE FORMATO — OBLIGATORIAS para ESTA respuesta]\n"
        "REGLA 1 — CERO META-LENGUAJE: PROHIBIDO decir 'La herramienta X', 'ToolMessage', 'ejecutada con éxito', "
        "'se ha obtenido', 'el sistema devolvió'. Habla directamente. Si usaste list_gmail, di 'Tus correos:'. "
        "Si usaste create_note, di 'Listo, guardé la nota.'\n"
        "REGLA 2 — MOSTRAR TODO: Si recibes correos, muéstralos TODOS con remitente y asunto. "
        "Si recibes links de Drive como [Nombre](https://...), cópialos EXACTOS. NO resumas en 'encontré 3 archivos'.\n"
        "REGLA 3 — IMÁGENES: Si buscar_imagenes_web devuelve ![titulo](url), copia esos bloques EXACTOS "
        "en tu respuesta. Nunca digas 'no se encontraron imágenes' si el resultado contiene URLs de imagen.\n"
        "REGLA 4 — NO INVENTES: NUNCA crees notas, tareas o eventos que el usuario NO pidió en ESTE mensaje. "
        "Responde SOLO a lo que pide el mensaje actual. Ignora resultados de herramientas de mensajes anteriores.\n"
        "REGLA 5 — ANTI-ALUCINACIÓN (CRÍTICO): NUNCA mientas diciendo que ya buscaste en la web o leíste un archivo si no has llamado a la herramienta. Si debes usar una herramienta, EMITE EL TOOL_CALL y NO devuelvas texto asumiendo el resultado. ¡Debes ESPERAR a que la herramienta te devuelva la información real!"
    )

    # Inject rules right before the last HumanMessage in the history
    last_is_tool = bool(base) and isinstance(base[-1], ToolMessage)
    enriched = list(base)
    if extra_context and enriched and not last_is_tool:
        if len(extra_context) > 6000:
            extra_context = extra_context[:6000] + "\n\n...[CONTEXTO TRUNCADO]..."
        ctx = HumanMessage(content="[INFORMACIÓN RELEVANTE DE TU MEMORIA EXTERNA]\n" + extra_context)
        enriched = enriched[:-1] + [ctx, enriched[-1]]

    # Find last HumanMessage and inject behavior rules before it
    last_human_idx = None
    for i in range(len(enriched) - 1, -1, -1):
        if isinstance(enriched[i], HumanMessage):
            last_human_idx = i
            break
    if last_human_idx is not None and last_human_idx > 0:
        rules_msg = HumanMessage(content=behavior_rules)
        enriched = enriched[:last_human_idx] + [rules_msg] + enriched[last_human_idx:]

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
