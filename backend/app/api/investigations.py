from pathlib import Path

from fastapi import APIRouter, HTTPException
from app.core.constants import (
    DEFAULT_MAX_CORRELATED_EVENTS,
    DEFAULT_MAX_CORRELATION_DEPTH,
)
from app.engine.correlation import CorrelatedEvent as CorrelatedEventData
from app.engine.intelligence import investigate_events
from app.models.investigation import (
    CorrelatedEvent,
    CorrelationStatistics,
    FailureFinding,
    InvestigationRequest,
    InvestigationTimeWindow,
    InvestigationResult,
)
from app.sources.synthetic import SyntheticSource

router = APIRouter(prefix="/api/v1", tags=["investigations"])
FIXTURE = Path(__file__).resolve().parents[3] / "samples" / "incident_001.json"


@router.post("/investigations", response_model=InvestigationResult)
def investigate(request: InvestigationRequest) -> InvestigationResult:
    candidates = SyntheticSource(FIXTURE).fetch_all()
    try:
        analysis = investigate_events(
            candidates,
            request.identifier_type,
            request.identifier_value,
            reference_timestamp=request.reference_timestamp,
        )
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    def response_event(item: CorrelatedEventData) -> CorrelatedEvent:
        return CorrelatedEvent(
            **item.event.model_dump(),
            correlation_type=item.correlation_type,
            depth=item.depth,
            parent_event_id=item.parent_event_id,
            matched_identifier_key=item.matched_identifier_key,
            matched_identifier_value=item.matched_identifier_value,
        )

    result = analysis.correlation
    events = [response_event(item) for item in result.events]
    timeline = [response_event(item) for item in analysis.timeline]
    findings = [
        FailureFinding(
            event_id=item.event_id,
            service=item.service,
            timestamp=item.timestamp,
            severity=item.severity,
            evidence=list(item.evidence),
        )
        for item in analysis.findings
    ]
    limitations = [
        "Candidate events come from a synthetic JSON fixture.",
        *analysis.limitations,
    ]
    if result.truncated:
        limitations.append(
            f"Results were truncated at the {DEFAULT_MAX_CORRELATED_EVENTS}-event limit."
        )

    return InvestigationResult(
        identifier_type=request.identifier_type,
        identifier_value=request.identifier_value,
        events=events,
        summary=analysis.summary,
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
        status=analysis.status,
        effective_time_window=InvestigationTimeWindow(
            start=analysis.window_start,
            end=analysis.window_end,
            duration_minutes=analysis.window_minutes,
        ),
        findings=findings,
        timeline=timeline,
    )
