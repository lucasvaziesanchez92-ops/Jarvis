"""OpenAI provider (or any OpenAI-compatible API endpoint).

Best for tool-calling consistency. Use gpt-4o-mini for cheap + fast,
gpt-4o for best quality. Compatible endpoints: OpenRouter, Together,
Groq, OpenAI, Azure OpenAI.
"""
from langchain_openai import ChatOpenAI

from backend.config import settings


def get_llm():
    """Return a ChatOpenAI instance configured for tool-calling.

    For tool-calling, the recommended model is gpt-4o-mini: it's cheap
    (~$0.15/M input tokens), fast (~1-2s first token), and handles
    30+ tools reliably without hallucinating.
    """
    kwargs = {
        "model": settings.openai_model,
        "api_key": settings.openai_api_key,
        "temperature": 0.2,  # low for tool-calling consistency
        "model_kwargs": {
            "frequency_penalty": 1.2,
        },
    }
    if settings.openai_base_url and settings.openai_base_url != "https://api.openai.com/v1":
        kwargs["base_url"] = settings.openai_base_url
    return ChatOpenAI(**kwargs)
