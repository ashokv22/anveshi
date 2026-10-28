import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal

from app.core.constants import DEFAULT_INVESTIGATION_WINDOW_MINUTES
from app.engine.correlation import CorrelationResult, CorrelatedEvent, correlate
from app.models.event import Event


@dataclass(frozen=True)
class FailureFinding:
    event_id: str
    service: str
    timestamp: datetime
    severity: str
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class InvestigationAnalysis:
    correlation: CorrelationResult
    timeline: list[CorrelatedEvent]
    findings: list[FailureFinding]
    status: Literal[
        "no_events", "failures_detected", "no_failures_detected", "incomplete"
    ]
    summary: str
    window_start: datetime | None
    window_end: datetime | None
    window_minutes: int
    limitations: list[str]


_FAILURE_STATUS_VALUES = frozenset(
    {"error", "failed", "failure", "fatal", "timeout", "timed_out"}
)
_FAILURE_STATUS_KEYS = frozenset(
    {"status", "status_code", "outcome", "result", "state"}
)
_TIMEOUT_PATTERN = re.compile(
    r"\b(timeout|timed[\s-]?out|deadline exceeded)\b", re.IGNORECASE
)
_HTTP_5XX_PATTERN = re.compile(r"\bHTTP(?:/\d(?:\.\d)?)?\s+(5\d{2})\b", re.IGNORECASE)


def _failure_evidence(event: Event) -> tuple[str, ...]:
    evidence: list[str] = []
    structured_http_5xx = False
    severity = (event.level or "").strip().upper()
    if severity in {"ERROR", "FATAL"}:
        evidence.append(f"severity={severity}")

    for key, value in sorted(event.attributes.items()):
        normalized_key = key.rsplit(".", 1)[-1].lower()
        if normalized_key in {"http.status", "http.status_code", "status_code"}:
            try:
                status_code = int(value)
            except (TypeError, ValueError):
                continue
            if 500 <= status_code <= 599:
                evidence.append(f"{key}={value} (HTTP 5xx)")
                structured_http_5xx = True
        elif normalized_key in _FAILURE_STATUS_KEYS:
            if isinstance(value, str) and value.strip().lower() in _FAILURE_STATUS_VALUES:
                evidence.append(f"{key}={value}")
            elif normalized_key in {"status", "status_code"}:
                try:
                    status_code = int(value)
                except (TypeError, ValueError):
                    continue
                if 500 <= status_code <= 599:
                    evidence.append(f"{key}={value} (HTTP 5xx)")
                    structured_http_5xx = True
        elif normalized_key in {"success", "is_successful"} and value is False:
            evidence.append(f"{key}=false")

    message_status = _HTTP_5XX_PATTERN.search(event.message)
    if message_status and not structured_http_5xx:
        evidence.append(f"message contains HTTP {message_status.group(1)}")
    if _TIMEOUT_PATTERN.search(event.message):
        evidence.append("message contains a timeout indicator")

    for key, value in sorted(event.attributes.items()):
        normalized_key = key.rsplit(".", 1)[-1].lower()
        if normalized_key in {"timeout", "timed_out", "deadline_exceeded"}:
            if value is True or (
                isinstance(value, str)
                and value.strip().lower() in {"true", "yes", "1"}
            ):
                evidence.append(f"{key}={value}")
    return tuple(evidence)


def detect_failures(events: list[CorrelatedEvent]) -> list[FailureFinding]:
    findings = []
    for correlated in events:
        event = correlated.event
        evidence = _failure_evidence(event)
        if evidence:
            findings.append(
                FailureFinding(
                    event_id=event.event_id,
                    service=event.service,
                    timestamp=event.timestamp,
                    severity=event.level or "UNKNOWN",
                    evidence=evidence,
                )
            )
    return findings


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("reference_timestamp must include timezone information")
    return value.astimezone(timezone.utc)


def _direct_matches(
    events: list[Event], identifier_key: str, identifier_value: str
) -> list[Event]:
    return sorted(
        (
            event
            for event in events
            if event.identifiers.get(identifier_key) == identifier_value
        ),
        key=lambda event: (event.timestamp, event.event_id),
    )


def _summary(
    correlation: CorrelationResult,
    findings: list[FailureFinding],
    status: str,
) -> str:
    if status == "no_events":
        return "No matching events were found; no failure or cause can be determined."
    if status == "incomplete":
        return (
            f"Investigation is incomplete: {len(correlation.events)} correlated event(s), "
            f"{len(findings)} failure finding(s); root cause is unknown."
        )
    if findings:
        services = ", ".join(sorted({finding.service for finding in findings}))
        return (
            f"Found {len(correlation.events)} correlated event(s) and "
            f"{len(findings)} failure finding(s) in {services}; "
            "root cause is unknown."
        )
    return (
        f"Found {len(correlation.events)} correlated event(s) with no detected "
        "failure indicators; root cause is unknown."
    )


def investigate_events(
    events: list[Event],
    identifier_key: str,
    identifier_value: str,
    reference_timestamp: datetime | None = None,
    window_minutes: int = DEFAULT_INVESTIGATION_WINDOW_MINUTES,
) -> InvestigationAnalysis:
    if not isinstance(window_minutes, int) or isinstance(window_minutes, bool) or window_minutes <= 0:
        raise ValueError("window_minutes must be a positive integer")

    direct_matches = _direct_matches(events, identifier_key, identifier_value)
    if reference_timestamp is not None:
        window_start = _utc(reference_timestamp)
    elif direct_matches:
        window_start = _utc(direct_matches[0].timestamp)
    else:
        window_start = None

    window_end = (
        window_start + timedelta(minutes=window_minutes)
        if window_start is not None
        else None
    )
    if window_start is None:
        within_window = events
    else:
        within_window = [
            event
            for event in events
            if window_start <= _utc(event.timestamp) <= window_end
        ]

    correlation = correlate(within_window, identifier_key, identifier_value)
    timeline = sorted(
        correlation.events,
        key=lambda item: (item.event.timestamp, item.event.event_id),
    )
    findings = detect_failures(timeline)
    if not correlation.events:
        status: Literal[
            "no_events", "failures_detected", "no_failures_detected", "incomplete"
        ] = "no_events"
    elif correlation.truncated:
        status = "incomplete"
    elif findings:
        status = "failures_detected"
    else:
        status = "no_failures_detected"

    limitations = [
        "Failure findings identify observed indicators only; they do not establish root cause."
    ]
    if window_start is not None:
        limitations.append(
            "Only candidate events within the inclusive effective time window were considered."
        )
    if correlation.truncated:
        limitations.append(
            "The correlated event limit was reached; additional evidence may be omitted."
        )

    return InvestigationAnalysis(
        correlation=correlation,
        timeline=timeline,
        findings=findings,
        status=status,
        summary=_summary(correlation, findings, status),
        window_start=window_start,
        window_end=window_end,
        window_minutes=window_minutes,
        limitations=limitations,
    )
