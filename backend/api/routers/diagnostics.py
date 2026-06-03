"""Diagnostic endpoints for agent health and memory."""
from fastapi import APIRouter

from backend.services.memory_service import memory_service

router = APIRouter(prefix="/diagnostics", tags=["diagnostics"])


@router.get("/health")
async def agent_health():
    """Quick health check of the agent's memory and diagnostics system."""
    return memory_service.get_health()


@router.get("/report")
async def diagnostic_report():
    """Full diagnostic report of the agent."""
    return memory_service.run_diagnose()


@router.post("/cleanup")
async def agent_cleanup(compact_days: int = 30):
    """Run CCleaner-style cleanup: compact memory, clear old errors."""
    return memory_service.run_cleanup(compact_days=compact_days)


@router.get("/memory/categories")
async def memory_categories():
    """List all memory categories with counts."""
    return memory_service.list_categories()
