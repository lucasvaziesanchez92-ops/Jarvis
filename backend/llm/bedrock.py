"""Factory for the Bedrock LLM — returns a provider-agnostic BaseChatModel."""
from langchain_aws import ChatBedrockConverse
from langchain_core.language_models import BaseChatModel

from backend.config import settings


def get_llm() -> BaseChatModel:
    """Return a ChatBedrockConverse instance configured from settings."""
    kwargs: dict = {
        "model_id": settings.bedrock_model_id,
        "region_name": settings.aws_region,
    }
    if settings.aws_access_key_id and settings.aws_secret_access_key:
        kwargs["aws_access_key_id"] = settings.aws_access_key_id
        kwargs["aws_secret_access_key"] = settings.aws_secret_access_key

    return ChatBedrockConverse(**kwargs)
