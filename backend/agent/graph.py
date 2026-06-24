"""Graph — semantic tool routing + token budget + parallel tools."""
import json
from typing import Literal

from langgraph.graph import StateGraph, START, END
from langchain_core.messages import ToolMessage, SystemMessage
from loguru import logger

from backend.agent.state import JarvisState
from backend.agent.nodes import call_model_with_tools
from backend.agent.rag_node import retrieval_node
from backend.tools.semantic_router import ToolRouter

MAX_TOOL_ITERATIONS = 5
_router = None


def _get_router():
    global _router
    if _router is None:
        from backend.tools.registry import ALL_TOOLS
        _router = ToolRouter(ALL_TOOLS)
    return _router


def tools_condition(state: JarvisState) -> Literal["tools", "__end__"]:
    messages = state["messages"]
    if not messages:
        return "__end__"
    last = messages[-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"
    return "__end__"


def agent_node(state: JarvisState) -> dict:
    from backend.llm import get_llm
    from backend.tools.registry import ALL_TOOLS
    from backend.agent.personalities import get_persona
    from backend.core.token_budget import manage_context
    from backend.services.lancedb_cache import semantic_cache
    from backend.agent.profiler import analizar_y_guardar_perfil
    import asyncio

    persona = state.get("persona", "profesional")
    iterations = state.get("tool_iterations", 0)
    tools_executed = state.get("tools_executed", [])

    if iterations >= MAX_TOOL_ITERATIONS:
        llm = get_llm()
        executed_context = "Ya tienes toda la información de las herramientas en tu contexto. Responde directamente con los resultados obtenidos y consolida todo de forma fluida."
        stop = SystemMessage(content=f"{executed_context}\nNunca menciones que ejecutaste herramientas ni sus nombres técnicos.")
        response = llm.invoke([stop] + state["messages"])
        return {"messages": [response], "tools_executed": tools_executed}

    persona_config = get_persona(persona)
    allowed = set(persona_config.allowed_tools)
    persona_tools = [t for t in ALL_TOOLS if t.name in allowed]

    last_user_msg = ""
    for m in reversed(state["messages"]):
        if hasattr(m, "type") and m.type == "human":
            last_user_msg = m.content if hasattr(m, "content") else ""
            break

    if last_user_msg:
        tools = _get_router().route(last_user_msg, top_k=20)
        persona_names = {t.name for t in persona_tools}
        tools = [t for t in tools if t.name in persona_names]

        # ALWAYS include all available Google tools if OAuth is configured.
        # The TF-IDF router otherwise drops them on generic queries like
        # "test all your tools", and the LLM hallucinates that the tools
        # don't exist. Better to show the LLM every available tool than
        # to filter too aggressively.
        for pt in persona_tools:
            if pt.name.startswith(("list_gmail", "search_gmail", "send_gmail",
                                    "list_drive", "search_drive", "read_drive",
                                    "get_drive", "upload_drive", "delete_drive",
                                    "analyze_drive", "list_calendar_google",
                                    "create_calendar_event_google")):
                if pt not in tools:
                    tools.append(pt)

        # Keyword-boost: if the user mentions specific domains explicitly,
        # make sure the relevant tools are in the list.
        q_lower = last_user_msg.lower()
        keyword_tool_map = {
            (
                "drive", "google drive", "archivo", "archivos", "fichero", "ficheros",
                "documento", "documentos", "imagen", "imagenes", "foto", "fotos",
                "qr", "codigo qr", "código qr", "buscalo", "busca", "en mi drive",
                "en mi unidad", "mi nube", "nube",
            ): [
                "search_drive", "list_drive_files", "list_drive_folder",
                "read_drive_file", "get_drive_file_info", "upload_drive_file",
                "delete_drive_file", "analyze_drive_image",
            ],
            (
                "mail", "gmail", "correo", "correos", "email", "emails",
                "inbox", "bandeja", "mensaje", "mensajes",
            ): [
                "list_gmail", "search_gmail", "send_gmail",
                "get_gmail_detail", "delete_gmail_message", "trash_gmail_message",
            ],
            (
                "calendar", "calendario", "evento", "eventos", "reunion", "reunión",
                "agenda", "agendar", "agendame", "cita", "citas",
            ): [
                "list_calendar_events", "create_calendar_event",
                "update_calendar_event", "delete_calendar_event",
                "list_calendar_google", "create_calendar_event_google",
            ],
            ("storage", "bucket", "subido", "subir archivo", "guardar archivo"): [
                "list_storage_files", "read_storage_file", "delete_storage_file",
            ],
            ("clima", "tiempo", "temperatura", "llover", "lluvia", "frio", "calor", "weather"): [
                "get_weather",
            ],
            ("calcula", "calcular", "matematicas", "matemáticas", "porcentaje", "multiplica", "divide", "suma", "resta", "math"): [
                "calculate_math",
            ],
            ("hora", "que hora", "fecha", "dia es hoy", "día es hoy"): [
                "get_current_time", "get_current_date",
            ],
        }
        for keywords, tool_names in keyword_tool_map.items():
            if any(kw in q_lower for kw in keywords):
                for tn in tool_names:
                    for pt in persona_tools:
                        if pt.name == tn and pt not in tools:
                            tools.append(pt)
                            break

        # Always include the most-used critical tools
        critical = {"create_note", "create_todo", "wiki_query", "web_search"}
        for critical_name in critical:
            for pt in persona_tools:
                if pt.name == critical_name and pt not in tools:
                    tools.append(pt)
        # NO MORE 15-tool cap. The previous cap was dropping Google
        # tools the user expected ('buscalo en mi drive' was missing
        # search_drive). The LLM is now able to handle 40+ tools
        # (devstral-small-2:24b has 32k context, plenty for schemas).
        # We still cap at len(persona_tools) so the persona's
        # allowed set is respected.
        tools = tools[: len(persona_tools)]
    else:
        tools = list(persona_tools)

    retrieved = "\n".join(state.get("retrieved_context", [])) if state.get("retrieved_context") else ""

    # 1. Recuperar los hechos biográficos desde el almacenamiento local incrustado (<2ms)
    try:
        hechos_perfil = semantic_cache.obtener_perfil_completo()
        if hechos_perfil:
            bloque_memoria = "[MEMORIA PERMANENTE DEL USUARIO]\n"
            for hecho in hechos_perfil:
                bloque_memoria += f"- {hecho}\n"
            retrieved = bloque_memoria + "\n" + retrieved if retrieved else bloque_memoria
    except Exception as e:
        logger.error(f"Error fetching user profile: {e}")

    # 3. EXTRACCIÓN ASÍNCRONA DESACOPLADA (El truco de velocidad)
    if last_user_msg:
        try:
            import threading
            def run_profiler():
                try:
                    asyncio.run(analizar_y_guardar_perfil(last_user_msg))
                except Exception as ex:
                    logger.error(f"Profiler thread error: {ex}")
            
            threading.Thread(target=run_profiler, daemon=True).start()
        except Exception as e:
            logger.error(f"Error starting profiler task: {e}")

    if tools_executed and iterations > 0:
        tool_context = f"[CONTEXTO: Ya ejecutaste estas herramientas en este turno: {', '.join(tools_executed)}. No las repitas a menos que sea necesario.]"
        if retrieved:
            retrieved = tool_context + "\n" + retrieved
        else:
            retrieved = tool_context

    logger.info(f"Agent: {len(tools)}/{len(persona_tools)} tools routed, executed={tools_executed}, persona={persona}")

    llm = get_llm()
    llm_with_tools = llm.bind_tools(tools)

    try:
        result = call_model_with_tools(state, llm_with_tools=llm_with_tools, extra_context=retrieved)
    except Exception as e:
        logger.warning(f"bind_tools falló ({e}), usando invoke plano")
        llm2 = get_llm()
        result = {"messages": [llm2.invoke(state["messages"])]}

    result["tool_iterations"] = iterations
    result["tools_executed"] = tools_executed
    return result


async def tool_node(state: JarvisState) -> dict:
    from backend.tools.registry import ALL_TOOLS
    from backend.api.routers.diagnostics import record_error
    import asyncio

    messages = state["messages"]
    last = messages[-1]
    tools_executed = state.get("tools_executed", [])

    if not (hasattr(last, "tool_calls") and last.tool_calls):
        logger.warning(f"tool_node: no tool_calls in last message ({type(last).__name__})")
        return {"messages": []}

    from backend.tools.registry import TOOL_ALIASES
    tool_map = {t.name: t for t in ALL_TOOLS}
    
    async def _run_tool(tc):
        raw_name = tc["name"]
        canonical = TOOL_ALIASES.get(raw_name, raw_name)
        name = canonical
        raw_args = tc.get("args", {}) or {}
        logger.info(f"tool_node: executing {name}({json.dumps(raw_args, default=str)[:200]})")
        t = tool_map.get(name)
        if t:
            try:
                schema = getattr(t, "args_schema", None)
                missing = []
                coerced = dict(raw_args)
                if schema is not None and hasattr(schema, "model_fields"):
                    for fname, finfo in schema.model_fields.items():
                        if fname not in coerced or coerced[fname] in (None, ""):
                            is_required = finfo.is_required() if callable(getattr(finfo, "is_required", None)) else True
                            if is_required:
                                missing.append(fname)
                    if missing:
                        if missing == ["content"] and name.startswith("create_"):
                            coerced["content"] = "(contenido no especificado)"
                            missing = []
                if missing:
                    msg = (
                        f"Error: la herramienta '{name}' requiere los campos "
                        f"{missing} que no fueron provistos. Reformula tu llamada "
                        f"incluyendo esos argumentos."
                    )
                    return ToolMessage(content=msg, tool_call_id=tc["id"], name=name), None
                
                # Ejecución asíncrona para mayor concurrencia
                if hasattr(t, "ainvoke") and callable(t.ainvoke):
                    out = str(await t.ainvoke(coerced))
                else:
                    out = str(await asyncio.to_thread(t.invoke, coerced))
                    
                logger.opt(colors=False).info(f"tool_node: {name} returned {len(out)} chars: {out[:200]}")
                return ToolMessage(content=out, tool_call_id=tc["id"], name=name), name
            except Exception as ex:
                logger.error("Tool '{}' crashed: {}: {}", name, type(ex).__name__, str(ex), exc_info=True)
                record_error("tool_node", ex, {"tool": name, "args": raw_args})
                return ToolMessage(content=f"Error: {type(ex).__name__}: {str(ex)[:200]}", tool_call_id=tc["id"], name=name), None
        else:
            logger.error(f"tool_node: tool '{name}' not found in registry ({len(tool_map)} tools loaded)")
            return ToolMessage(
                content=f"Herramienta '{name}' no encontrada. Disponibles: {', '.join(sorted(tool_map.keys()))[:200]}",
                tool_call_id=tc["id"], name=name,
            ), None

    # Ejecutar todas las herramientas en paralelo masivo
    tasks = [_run_tool(tc) for tc in last.tool_calls]
    results = await asyncio.gather(*tasks)

    messages_out = []
    for msg, executed_name in results:
        messages_out.append(msg)
        if executed_name and executed_name not in tools_executed:
            tools_executed.append(executed_name)

    return {
        "messages": messages_out,
        "tool_iterations": state.get("tool_iterations", 0) + 1,
        "tools_executed": tools_executed,
    }


def build_autonomous_graph(tools=None):
    """Build the agent graph.

    NO checkpointer: the WS router already manages session history
    in the frontend store. Using InMemorySaver here caused the
    OpenAI error 'Not the same number of function calls and
    responses' because the checkpointer re-injected old AIMessage
    (with stale tool_calls) into the next turn's input, and the
    new LLM tool_call didn't match.
    """
    from backend.agent.knowledge_extractor import extract_knowledge
    
    builder = StateGraph(JarvisState)

    builder.add_node("retrieval", retrieval_node)
    builder.add_node("agent", agent_node)
    builder.add_node("tools", tool_node)
    builder.add_node("extractor", extract_knowledge)
    
    builder.add_edge(START, "retrieval")
    builder.add_edge("retrieval", "agent")
    builder.add_conditional_edges("agent", tools_condition, {"tools": "tools", "__end__": "extractor"})
    builder.add_edge("tools", "agent")
    builder.add_edge("extractor", END)

    return builder.compile()


_graph = None


def get_graph(tools=None):
    global _graph
    if _graph is None or tools is not None:
        _graph = build_autonomous_graph(tools=tools)
    return _graph
