from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # AWS / Bedrock
    aws_region: str = Field(default="us-east-1", alias="AWS_REGION")
    aws_access_key_id: str | None = Field(default=None, alias="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: str | None = Field(default=None, alias="AWS_SECRET_ACCESS_KEY")
    bedrock_model_id: str = Field(
        default="us.anthropic.claude-sonnet-4-5",
        alias="BEDROCK_MODEL_ID",
    )

    # Ollama (Local/Cloud LLM)
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="llama3.2", alias="OLLAMA_MODEL_ID")
    ollama_api_key: str = Field(default="", alias="OLLAMA_API_KEY")

    # LM Studio (OpenAI-compatible local LLM)
    lm_studio_base_url: str = Field(default="http://127.0.0.1:1234/v1", alias="LM_STUDIO_BASE_URL")
    lm_studio_model: str = Field(default="qwen/qwen2.5-vl-7b", alias="LM_STUDIO_MODEL")

    # LLM Provider: "bedrock" or "ollama" or "lm_studio"
    llm_provider: str = Field(default="ollama", alias="LLM_PROVIDER")

    # Storage
    data_dir: str = Field(default="data", alias="DATA_DIR")
    storage_type: str = Field(default="sqlite", alias="STORAGE_TYPE")
    database_url: str | None = Field(default=None, alias="DATABASE_URL")

    # Obsidian Vault
    obsidian_vault_path: str = Field(default="", alias="OBSIDIAN_VAULT_PATH")

    # Memory
    max_context_messages: int = Field(default=50, alias="MAX_CONTEXT_MESSAGES")

    # Web Search
    tavily_api_key: str | None = Field(default=None, alias="TAVILY_API_KEY")

    # Observability
    enable_langsmith: bool = Field(default=False, alias="ENABLE_LANGSMITH")
    langsmith_api_key: str | None = Field(default=None, alias="LANGSMITH_API_KEY")

    # Gmail (Phase 2)
    gmail_credentials_file: str | None = Field(default=None, alias="GMAIL_CREDENTIALS_FILE")
    gmail_token_file: str | None = Field(default=None, alias="GMAIL_TOKEN_FILE")

    # Google Calendar
    gcal_token_file: str | None = Field(default=None, alias="GCAL_TOKEN_FILE")

    # API
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    cors_origins: list[str] = Field(default=["*"], alias="CORS_ORIGINS")

    # Security & Auth
    jwt_secret_key: str = Field(
        default="change-this-to-a-random-secret-key-in-production",
        alias="JWT_SECRET_KEY",
    )
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")

    # Speech (Groq STT + Piper TTS)
    groq_api_key: str | None = Field(default=None, alias="GROQ_API_KEY")
    groq_stt_model: str = Field(default="whisper-large-v3", alias="GROQ_STT_MODEL")
    piper_model_path: str = Field(
        default="data/voices/es_ES-davefx-medium.onnx",
        alias="PIPER_MODEL_PATH",
    )


    rate_limit_default: str = Field(default="100/minute", alias="RATE_LIMIT_DEFAULT")
    rate_limit_chat: str = Field(default="10/minute", alias="RATE_LIMIT_CHAT")
    rate_limit_agent: str = Field(default="20/minute", alias="RATE_LIMIT_AGENT")


settings = Settings()
