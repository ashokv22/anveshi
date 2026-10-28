from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator
from app.models.event import Event


class InvestigationRequest(BaseModel):
    identifier_type: str = Field(min_length=1)
    identifier_value: str = Field(min_length=1)
    reference_timestamp: datetime | None = None

    @field_validator("identifier_type", "identifier_value")
    @classmethod
    def require_non_whitespace(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Investigation identifier cannot be empty")
        return value

    @field_validator("reference_timestamp")
    @classmethod
    def require_timezone_on_reference(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("reference_timestamp must include timezone information")
        return value


class CorrelatedEvent(Event):
    correlation_type: Literal["direct", "discovered"]
    depth: int = Field(ge=0)
    parent_event_id: str | None = None
    matched_identifier_key: str
    matched_identifier_value: str


class CorrelationStatistics(BaseModel):
    direct_count: int
    discovered_count: int
    total_count: int
    depth_reached: int
    max_depth: int
    max_events: int


class InvestigationTimeWindow(BaseModel):
    start: datetime | None
    end: datetime | None
    duration_minutes: int


class FailureFinding(BaseModel):
    event_id: str
    service: str
    timestamp: datetime
    severity: str
    evidence: list[str]


class InvestigationResult(BaseModel):
    identifier_type: str
    identifier_value: str
    events: list[CorrelatedEvent] = Field(default_factory=list)
    summary: str
    limitations: list[str] = Field(default_factory=list)
    correlation_statistics: CorrelationStatistics
    truncated: bool
    status: Literal[
        "no_events", "failures_detected", "no_failures_detected", "incomplete"
    ]
    effective_time_window: InvestigationTimeWindow
    findings: list[FailureFinding] = Field(default_factory=list)
    timeline: list[CorrelatedEvent] = Field(default_factory=list)
