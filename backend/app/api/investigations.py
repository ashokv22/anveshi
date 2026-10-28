from pathlib import Path

from fastapi import APIRouter
from app.models.investigation import InvestigationRequest, InvestigationResult
from app.sources.synthetic import SyntheticSource

router = APIRouter(prefix="/api/v1", tags=["investigations"])
FIXTURE = Path(__file__).resolve().parents[3] / "samples" / "incident_001.json"


@router.post("/investigations", response_model=InvestigationResult)
def investigate(request: InvestigationRequest) -> InvestigationResult:
    events = SyntheticSource(FIXTURE).fetch(request.identifier_type, request.identifier_value)
    return InvestigationResult(
        identifier_type=request.identifier_type,
        identifier_value=request.identifier_value,
        events=events,
        summary=f"Found {len(events)} directly matching event(s). Investigation engine not yet implemented.",
        limitations=["Only direct matches from a synthetic fixture are available.",
                     "Correlation, timeline reconstruction, and failure detection are not implemented."],
    )
