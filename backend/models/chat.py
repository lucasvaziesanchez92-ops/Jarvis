from typing import Literal, Any
from pydantic import BaseModel, Field
import uuid


class FileAttachment(BaseModel):
    """Archivo adjunto subido al bucket."""
    key: str  # S3 object key
    filename: str
    size: int
    content_type: str


class ChatRequest(BaseModel):
    message: str
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = "default"
    persona: str = "profesional"
    attachments: list[FileAttachment] = Field(default_factory=list)


class ChatResponse(BaseModel):
    content: str
    session_id: str


class StreamChunk(BaseModel):
    type: Literal["token", "stream", "tool_start", "tool_end", "done", "error", "file_uploaded"]
    content: str = ""
    tool_name: str | None = None
    tool_input: dict[str, Any] | None = None
    tool_output: Any | None = None
    file_key: str | None = None  # Para notificar archivos subidos


# ── Voice Pipeline Models (Groq STT + Piper TTS) ─────────────

class TTSRequest(BaseModel):
    text: str


class TTSResponse(BaseModel):
    audio_base64: str


class VoicePipelineResponse(BaseModel):
    transcript: str
    response_text: str
    audio_base64: str
    session_id: str = ""

