"""Agent endpoint: POST /agent/run — structured agent response for mobile frontend.

This endpoint is designed specifically for the mobile app's agent-centric UX.
It returns structured data including actions, suggestions, and tool execution info.
"""
import json
import uuid

from fastapi import APIRouter, Depends
from langchain_core.messages import HumanMessage

from backend.api.dependencies import get_jarvis_graph
from backend.models.chat import ChatRequest

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/run")
async def agent_run(request: ChatRequest, graph=Depends(get_jarvis_graph)):
    """
    Structured agent response endpoint for mobile frontend.

    Request: { "input": str, "session_id": str }
    Response: {
        "message": str,
        "actions": [{"id": str, "label": str, "type": str, "payload": any}],
        "suggestions": [str],
        "tools_executed": [str],
        "session_id": str
    }
    """
    session_id = request.session_id or str(uuid.uuid4())

    config = {
        "configurable": {
            "thread_id": session_id,
        }
    }

    state = await graph.ainvoke(
        {
            "messages": [HumanMessage(content=request.message)],
            "user_id": request.user_id,
            "session_id": session_id,
        },
        config=config,
    )

    ai_message = state["messages"][-1]
    content = ai_message.content

    # Build structured response
    # Parse the AI content to extract actions and suggestions
    actions = _extract_actions(content)
    suggestions = _generate_suggestions(content)
    tools_executed = _extract_tools_executed(state)

    return {
        "message": content,
        "actions": actions,
        "suggestions": suggestions,
        "tools_executed": tools_executed,
        "session_id": session_id,
    }


def _extract_actions(content: str) -> list[dict]:
    """Extract actions from AI response text.

    Parses the response for patterns like:
    - 'I've created...' -> action to view
    - 'I've scheduled...' -> action to view
    - etc.
    """
    actions = []

    # Check for common action patterns
    lines = content.split('\n')
    for line in lines:
        line_lower = line.lower().strip()

        if any(keyword in line_lower for keyword in ['cread', 'created', 'agend', 'scheduled', 'organizada']):
            actions.append({
                "id": str(uuid.uuid4())[:8],
                "label": "Ver detalle",
                "type": "view",
                "payload": {"text": line.strip()},
            })

        if any(keyword in line_lower for keyword in ['recordatori', 'reminder', 'alert']):
            actions.append({
                "id": str(uuid.uuid4())[:8],
                "label": "Editar recordatorio",
                "type": "edit",
                "payload": {"text": line.strip()},
            })

    return actions


def _generate_suggestions(content: str) -> list[str]:
    """Generate follow-up suggestions based on AI response content."""
    suggestions = []
    content_lower = content.lower()

    # Context-aware suggestions
    if any(kw in content_lower for kw in ['tarea', 'task', 'cread', 'created']):
        suggestions.append("¿Quieres agregar otra tarea?")
        suggestions.append("Ver todas mis tareas")

    if any(kw in content_lower for kw in ['agenda', 'horario', 'schedule', 'calendar']):
        suggestions.append("Optimiza mi horario")
        suggestions.append("Ver mi agenda")

    if any(kw in content_lower for kw in ['email', 'correo', 'mail']):
        suggestions.append("Revisa emails importantes")
        suggestions.append("Enviar email")

    if any(kw in content_lower for kw in ['compra', 'shop', 'super', 'lista']):
        suggestions.append("Sugerir lista de compras")
        suggestions.append("Programar compra")

    # Default suggestions
    if not suggestions:
        suggestions = ["¿Qué tengo pendiente?", "Optimiza mi día", "Revisa mis tareas"]

    return suggestions[:4]  # Max 4 suggestions


def _extract_tools_executed(state: dict) -> list[str]:
    """Extract list of tools that were executed during this run."""
    tools = []
    messages = state.get("messages", [])

    for msg in messages:
        # Check for tool call messages
        if hasattr(msg, 'tool_calls') and msg.tool_calls:
            for tool_call in msg.tool_calls:
                tool_name = tool_call.get("name", "")
                if tool_name and tool_name not in tools:
                    tools.append(tool_name)

    return tools
