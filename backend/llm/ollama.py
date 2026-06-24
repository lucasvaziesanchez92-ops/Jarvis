"""Factory for Ollama LLM — local Ollama via ChatOllama."""
from langchain_ollama import ChatOllama
from langchain_core.language_models import BaseChatModel
from backend.config import settings


def get_llm() -> BaseChatModel:
    return ChatOllama(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url.rstrip("/"),
        temperature=0.2,
        streaming=True,
        repeat_penalty=1.2,
    )
