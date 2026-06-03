"""LLM provider factory — returns a BaseChatModel from the configured provider."""
from langchain_core.language_models import BaseChatModel

from backend.config import settings


def get_llm() -> BaseChatModel:
    """Return a chat model instance based on the configured provider and URL."""
    provider = settings.llm_provider.lower()
    base_url = settings.ollama_base_url.lower()

    if provider == "ollama":
        if "ollama.com" in base_url or base_url.startswith("https://"):
            from backend.llm.ollama_cloud import get_llm as get_ollama_cloud_llm
            return get_ollama_cloud_llm()
        else:
            from backend.llm.ollama import get_llm as get_local_ollama_llm
            return get_local_ollama_llm()
    elif provider == "bedrock":
        from backend.llm.bedrock import get_llm as get_bedrock_llm
        return get_bedrock_llm()
    elif provider == "lm_studio":
        from backend.llm.lm_studio import get_llm as get_lm_studio_llm
        return get_lm_studio_llm()
    else:
        raise ValueError(f"Unknown LLM provider: {settings.llm_provider}. Use 'ollama', 'bedrock', or 'lm_studio'.")
