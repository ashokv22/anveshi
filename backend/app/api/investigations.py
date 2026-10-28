from pathlib import Path

from fastapi import APIRouter, HTTPException
from app.core.constants import (
    DEFAULT_INVESTIGATION_WINDOW_MINUTES,
    DEFAULT_MAX_CORRELATED_EVENTS,
    DEFAULT_MAX_CORRELATION_DEPTH,
)
from app.engine.correlation import correlate
from app.models.investigation import (
    CorrelatedEvent,
    CorrelationStatistics,
    InvestigationRequest,
    InvestigationResult,
)
from app.sources.synthetic import SyntheticSource

router = APIRouter(prefix="/api/v1", tags=["investigations"])
FIXTURE = Path(__file__).resolve().parents[3] / "samples" / "incident_001.json"


@router.post("/investigations", response_model=InvestigationResult)
def investigate(request: InvestigationRequest) -> InvestigationResult:
    candidates = SyntheticSource(FIXTURE).fetch_all()
    try:
        result = correlate(candidates, request.identifier_type, request.identifier_value)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    events = [
        CorrelatedEvent(
            **item.event.model_dump(),
            correlation_type=item.correlation_type,
            depth=item.depth,
            parent_event_id=item.parent_event_id,
            matched_identifier_key=item.matched_identifier_key,
            matched_identifier_value=item.matched_identifier_value,
        )
        for item in result.events
    ]
    limitations = [
        "Candidate events come from a synthetic JSON fixture.",
        "Time-window filtering is not implemented "
        f"(configured investigation window: {DEFAULT_INVESTIGATION_WINDOW_MINUTES} minutes).",
    ]
    if result.truncated:
        limitations.append(
            f"Results were truncated at the {DEFAULT_MAX_CORRELATED_EVENTS}-event limit."
        )
    return InvestigationResult(
        identifier_type=request.identifier_type,
        identifier_value=request.identifier_value,
        events=events,
        summary=(
            f"Found {result.direct_count} direct and {result.discovered_count} "
            f"discovered event(s)."
        ),
        limitations=limitations,
        correlation_statistics=CorrelationStatistics(
            direct_count=result.direct_count,
            discovered_count=result.discovered_count,
            total_count=len(events),
            depth_reached=result.depth_reached,
            max_depth=DEFAULT_MAX_CORRELATION_DEPTH,
            max_events=DEFAULT_MAX_CORRELATED_EVENTS,
        ),
        truncated=result.truncated,
    )
