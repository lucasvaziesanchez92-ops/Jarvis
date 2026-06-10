"""Ollama Cloud LLM — singleton ChatOpenAI with connection reuse."""
from functools import lru_cache

import httpx
from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseChatModel
from backend.config import settings


@lru_cache
def get_llm() -> BaseChatModel:
    return ChatOpenAI(
        model=settings.ollama_model,
        api_key=settings.ollama_api_key,
        base_url=f"{settings.ollama_base_url.rstrip('/')}/v1",
        temperature=0.2,  # lower = better for tool-calling
        streaming=True,
        max_tokens=2048,  # raised from 512 — tool schemas + responses need more room
        timeout=httpx.Timeout(connect=15.0, read=90.0, write=15.0, pool=10.0),
    )
