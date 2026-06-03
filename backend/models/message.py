from datetime import datetime, timezone
from typing import Literal, Any
from uuid import uuid4
from pydantic import BaseModel, Field


class Message(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    thread_id: str
    role: Literal["user", "assistant", "system"] = "user"
    content: str
    metadata: dict[str, Any] | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
