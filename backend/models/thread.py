from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4
from pydantic import BaseModel, Field


class Thread(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str | None = None
    status: Literal["active", "archived", "deleted"] = "active"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict | None = None
