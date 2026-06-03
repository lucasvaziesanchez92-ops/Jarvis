"""LLM configuration endpoints for Jarvis backend."""
import httpx
from typing import Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.config import settings


router = APIRouter(prefix="/llm", tags=["llm"])


class LLMConfigureRequest(BaseModel):
    provider: str
    base_url: str | None = None
    model: str | None = None


class LLMConfigureResponse(BaseModel):
    status: str
    provider: str
    model: str
    base_url: str


class ProviderInfo(BaseModel):
    id: str
    name: str
    default_model: str
    default_base_url: str
    available_models: list[str] = []
    is_configured: bool = False


class ModelInfo(BaseModel):
    id: str
    name: str
    provider: str


class LLMStatusResponse(BaseModel):
    provider: str
    model: str
    status: str
    info: dict[str, Any]


class LLMProvidersResponse(BaseModel):
    providers: list[ProviderInfo]


class LLMModelsResponse(BaseModel):
    models: list[ModelInfo]


_ollama_default_models = ["llama3.2", "llama3.1", "mistral", "codellama", "phi3", "qwen2.5", "deepseek-r1"]
_lm_studio_default_models = ["qwen/qwen2.5-vl-7b", "lmstudio-community/*", "mistralai/*"]


async def _check_ollama_connectivity(base_url: str) -> tuple[bool, str]:
    """Check if Ollama is reachable and return status info."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{base_url.rstrip('/')}/api/tags")
            if response.status_code == 200:
                data = response.json()
                models = data.get("models", [])
                model_names = [m.get("name", m.get("model", "")) for m in models]
                return True, f"Ollama connected with {len(models)} models"
            return False, f"Ollama returned status {response.status_code}"
    except httpx.TimeoutException:
        return False, "Ollama connection timed out"
    except httpx.ConnectError:
        return False, "Cannot connect to Ollama"
    except Exception as e:
        return False, f"Ollama error: {str(e)}"


async def _check_lm_studio_connectivity(base_url: str) -> tuple[bool, str]:
    """Check if LM Studio is reachable and return status info."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{base_url.rstrip('/')}/models")
            if response.status_code == 200:
                data = response.json()
                models = data.get("data", []) if isinstance(data, dict) else data
                model_ids = [m.get("id", "") for m in models if isinstance(m, dict)]
                return True, f"LM Studio connected with {len(models)} models"
            return False, f"LM Studio returned status {response.status_code}"
    except httpx.TimeoutException:
        return False, "LM Studio connection timed out"
    except httpx.ConnectError:
        return False, "Cannot connect to LM Studio"
    except Exception as e:
        return False, f"LM Studio error: {str(e)}"


@router.get("/status", response_model=LLMStatusResponse)
async def get_llm_status():
    """Get current LLM provider status."""
    provider = settings.llm_provider.lower()
    model = ""
    base_url = ""

    if provider == "ollama":
        model = settings.ollama_model
        base_url = settings.ollama_base_url
        connected, info_msg = await _check_ollama_connectivity(base_url)
        status = "connected" if connected else "disconnected"
        return LLMStatusResponse(
            provider="ollama",
            model=model,
            status=status,
            info={"message": info_msg, "base_url": base_url},
        )
    elif provider == "lm_studio":
        model = settings.lm_studio_model
        base_url = settings.lm_studio_base_url
        connected, info_msg = await _check_lm_studio_connectivity(base_url)
        status = "connected" if connected else "disconnected"
        return LLMStatusResponse(
            provider="lm_studio",
            model=model,
            status=status,
            info={"message": info_msg, "base_url": base_url},
        )
    elif provider == "bedrock":
        model = settings.bedrock_model_id
        return LLMStatusResponse(
            provider="bedrock",
            model=model,
            status="connected",
            info={"region": settings.aws_region},
        )
    else:
        raise HTTPException(
            status_code=400,
            detail={"error": {"type": "unknown_provider", "message": f"Unknown provider: {provider}"}},
        )


@router.get("/providers", response_model=LLMProvidersResponse)
async def get_providers():
    """Get available LLM providers and their configuration."""
    ollama_connected, ollama_msg = await _check_ollama_connectivity(settings.ollama_base_url)
    lm_studio_connected, lm_studio_msg = await _check_lm_studio_connectivity(settings.lm_studio_base_url)

    current_provider = settings.llm_provider.lower()

    providers = [
        ProviderInfo(
            id="ollama",
            name="Ollama",
            default_model=settings.ollama_model,
            default_base_url=settings.ollama_base_url,
            available_models=_ollama_default_models,
            is_configured=ollama_connected,
        ),
        ProviderInfo(
            id="lm_studio",
            name="LM Studio",
            default_model=settings.lm_studio_model,
            default_base_url=settings.lm_studio_base_url,
            available_models=_lm_studio_default_models,
            is_configured=lm_studio_connected,
        ),
        ProviderInfo(
            id="bedrock",
            name="AWS Bedrock",
            default_model=settings.bedrock_model_id,
            default_base_url=f"https://bedrock.{settings.aws_region}.amazonaws.com",
            available_models=[settings.bedrock_model_id],
            is_configured=settings.aws_access_key_id is not None,
        ),
    ]

    return LLMProvidersResponse(providers=providers)


@router.get("/models", response_model=LLMModelsResponse)
async def get_models():
    """Get available models from the current LLM provider."""
    provider = settings.llm_provider.lower()

    if provider == "ollama":
        base_url = settings.ollama_base_url
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{base_url.rstrip('/')}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    models = data.get("models", [])
                    model_list = [
                        ModelInfo(
                            id=m.get("name", ""),
                            name=m.get("name", ""),
                            provider="ollama",
                        )
                        for m in models
                        if m.get("name")
                    ]
                    if not model_list:
                        raise HTTPException(
                            status_code=503,
                            detail={"error": {"type": "no_models", "message": "No models found in Ollama"}},
                        )
                    return LLMModelsResponse(models=model_list)
                else:
                    raise HTTPException(
                        status_code=503,
                        detail={"error": {"type": "provider_error", "message": f"Ollama returned {response.status_code}"}},
                    )
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=503,
                detail={"error": {"type": "provider_timeout", "message": "Ollama request timed out"}},
            )
        except httpx.ConnectError:
            raise HTTPException(
                status_code=503,
                detail={"error": {"type": "provider_unreachable", "message": "Cannot connect to Ollama"}},
            )

    elif provider == "lm_studio":
        base_url = settings.lm_studio_base_url
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{base_url.rstrip('/')}/models")
                if response.status_code == 200:
                    data = response.json()
                    models = data.get("data", []) if isinstance(data, dict) else data
                    model_list = [
                        ModelInfo(
                            id=m.get("id", ""),
                            name=m.get("id", "").split("/")[-1] if "/" in m.get("id", "") else m.get("id", ""),
                            provider="lm_studio",
                        )
                        for m in models
                        if isinstance(m, dict) and m.get("id")
                    ]
                    if not model_list:
                        raise HTTPException(
                            status_code=503,
                            detail={"error": {"type": "no_models", "message": "No models found in LM Studio"}},
                        )
                    return LLMModelsResponse(models=model_list)
                else:
                    raise HTTPException(
                        status_code=503,
                        detail={"error": {"type": "provider_error", "message": f"LM Studio returned {response.status_code}"}},
                    )
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=503,
                detail={"error": {"type": "provider_timeout", "message": "LM Studio request timed out"}},
            )
        except httpx.ConnectError:
            raise HTTPException(
                status_code=503,
                detail={"error": {"type": "provider_unreachable", "message": "Cannot connect to LM Studio"}},
            )

    elif provider == "bedrock":
        return LLMModelsResponse(
            models=[ModelInfo(id=settings.bedrock_model_id, name=settings.bedrock_model_id, provider="bedrock")]
        )

    else:
        raise HTTPException(
            status_code=400,
            detail={"error": {"type": "unknown_provider", "message": f"Unknown provider: {provider}"}},
        )


@router.post("/configure", response_model=LLMConfigureResponse)
async def configure_llm(config: LLMConfigureRequest):
    """Configure the LLM provider and model."""
    provider = config.provider.lower()

    if provider not in ("ollama", "lm_studio"):
        raise HTTPException(
            status_code=400,
            detail={"error": {"type": "invalid_provider", "message": "Provider must be 'ollama' or 'lm_studio'"}},
        )

    if provider == "ollama":
        base_url = config.base_url or settings.ollama_base_url
        model = config.model or settings.ollama_model

        connected, info_msg = await _check_ollama_connectivity(base_url)
        if not connected:
            raise HTTPException(
                status_code=503,
                detail={"error": {"type": "provider_unreachable", "message": info_msg}},
            )

        settings.llm_provider = "ollama"
        settings.ollama_base_url = base_url
        settings.ollama_model = model

        return LLMConfigureResponse(
            status="ok",
            provider="ollama",
            model=model,
            base_url=base_url,
        )

    elif provider == "lm_studio":
        base_url = config.base_url or settings.lm_studio_base_url
        model = config.model or settings.lm_studio_model

        connected, info_msg = await _check_lm_studio_connectivity(base_url)
        if not connected:
            raise HTTPException(
                status_code=503,
                detail={"error": {"type": "provider_unreachable", "message": info_msg}},
            )

        settings.llm_provider = "lm_studio"
        settings.lm_studio_base_url = base_url
        settings.lm_studio_model = model

        return LLMConfigureResponse(
            status="ok",
            provider="lm_studio",
            model=model,
            base_url=base_url,
        )

    raise HTTPException(
        status_code=400,
        detail={"error": {"type": "invalid_provider", "message": f"Unknown provider: {provider}"}},
    )