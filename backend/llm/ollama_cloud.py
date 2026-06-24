"""Ollama Cloud LLM — singleton ChatOpenAI with connection reuse.

Model choice rationale (see session: research/2026-06-10):
  - gpt-oss:120b was tried first but emits corrupted tool names
    (Ollama issue #11704, closed by #11759). LangGraph can't match
    those names against the schema and falls back to a "no tool"
    response. Caused the user to report "el LLM miente sobre sus
    tools".
  - qwen3.5:32b was second try — does NOT EXIST in Ollama Cloud
    (only :397b tag is published, too big for free tier RAM).
  - devstral-small-2:24b is the new default: 24B params, 51GB
    on disk, validated by Mistral for tool-calling / agentic
    workflows. Available in Ollama Cloud.
  - Set temperature=0 (was 0.2) — at 0.2 the model occasionally
    invents tools it doesn't have (LangGraph issue #7845).
"""
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
        temperature=0,  # was 0.2 — at 0.2 qwen3.5 sometimes hallucinates tool names
        streaming=True,
        max_tokens=2048,
        timeout=httpx.Timeout(connect=15.0, read=90.0, write=15.0, pool=10.0),
        model_kwargs={
            "frequency_penalty": 1.2,
            # tool_choice removed — was causing "problema de latencia" with
            # devstral-small-2:24b because Ollama Cloud expects tool_choice
            # to be omitted for the model to use its native tool-calling.
        },
    )
