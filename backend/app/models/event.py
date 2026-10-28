from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class EventSource(BaseModel):
    type: str = Field(min_length=1)
    reference: str = Field(min_length=1)


class Event(BaseModel):
    event_id: str = Field(min_length=1)
    timestamp: datetime
    service: str = Field(min_length=1)
    level: str | None = None
    message: str
    identifiers: dict[str, str] = Field(default_factory=dict)
    attributes: dict[str, Any] = Field(default_factory=dict)
    source: EventSource

    @field_validator("timestamp")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must include timezone information")
        return value
