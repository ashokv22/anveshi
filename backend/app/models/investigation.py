from pydantic import BaseModel, Field
from app.models.event import Event


class InvestigationRequest(BaseModel):
    identifier_type: str = Field(min_length=1)
    identifier_value: str = Field(min_length=1)


class InvestigationResult(BaseModel):
    identifier_type: str
    identifier_value: str
    events: list[Event] = Field(default_factory=list)
    summary: str
    limitations: list[str] = Field(default_factory=list)
