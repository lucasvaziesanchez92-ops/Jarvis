from datetime import datetime, timezone
from uuid import uuid4
from pydantic import BaseModel, Field


class CalendarEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    start_datetime: datetime
    end_datetime: datetime
    description: str = ""
    location: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
