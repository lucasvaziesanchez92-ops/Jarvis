"""Factory for LM Studio LLM — uses ChatOpenAI class for compatibility."""
from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseChatModel
from backend.config import settings

def get_llm() -> BaseChatModel:
    """Return a ChatOpenAI instance configured for LM Studio.

    Reads from env:
        - LM_STUDIO_BASE_URL (default: http://127.0.0.1:1234/v1)
        - LM_STUDIO_MODEL    (default: qwen/qwen2.5-vl-7b)
    """
    return ChatOpenAI(
        model=settings.lm_studio_model,
        api_key="not-needed",
        base_url=settings.lm_studio_base_url,
        temperature=0.7,
        streaming=True,
        max_tokens=2048,
    )
