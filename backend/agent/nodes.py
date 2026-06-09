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
        "REGLAS CRÍTICAS SOBRE HERRAMIENTAS:\n"
        "1. Si decidís usar una herramienta, emití el tool_call. NO describas su resultado en texto hasta ver el ToolMessage correspondiente.\n"
        "2. Si una herramienta falla, decí 'No pude ejecutar X porque Y'. NO inventes un resultado exitoso.\n"
        "3. Si el usuario pide algo concreto (crear nota, mandar mail, agendar evento) y vos no llamás a la tool, no podés afirmar que lo hiciste. Decí 'voy a hacerlo' o 'lo hago' SOLO cuando estés por emitir el tool_call.\n"
        "4. NUNCA digas 'listo, ya está guardado/creado/enviado' si no viste un ToolMessage confirmándolo.\n"
        "5. Si la herramienta devuelve error (credenciales faltantes, módulo no disponible, etc.), reportá el error tal cual al usuario, no finjas éxito."
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
