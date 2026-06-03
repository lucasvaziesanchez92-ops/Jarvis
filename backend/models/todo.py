from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4
from pydantic import BaseModel, Field


class Todo(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    text: str
    completed: bool = False
    priority: Literal["low", "medium", "high"] = "medium"
    due_date: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
