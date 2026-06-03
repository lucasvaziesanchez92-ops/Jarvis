from datetime import datetime
from pydantic import BaseModel, Field


class EmailMessage(BaseModel):
    message_id: str
    sender: str
    recipient: str
    subject: str
    body: str
    snippet: str
    date: datetime
    labels: list[str] = []
    is_read: bool = True
