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
        temperature=0.5,
        streaming=True,
        max_tokens=512,
        timeout=httpx.Timeout(connect=8.0, read=25.0, write=8.0, pool=5.0),
    )
