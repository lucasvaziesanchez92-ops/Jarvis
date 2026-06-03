"""REST endpoints for Agent Personalities."""
from fastapi import APIRouter

from backend.agent.personalities import get_all_personas, get_persona

router = APIRouter()


@router.get("/personas")
def list_personas():
    return get_all_personas()


@router.get("/personas/{persona_name}")
def get_persona_config(persona_name: str):
    persona = get_persona(persona_name)
    return {
        "name": persona.name,
        "label": persona.label,
        "description": persona.description,
        "system_prompt": persona.system_prompt,
        "allowed_tools": persona.allowed_tools,
        "icon": persona.icon,
    }