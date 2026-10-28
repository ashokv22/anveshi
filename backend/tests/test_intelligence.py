from datetime import datetime, timedelta, timezone

import pytest

from app.engine.intelligence import investigate_events
from app.models.event import Event, EventSource


START = datetime(2026, 10, 28, 10, 15, tzinfo=timezone.utc)


def make_event(
    event_id: str,
    timestamp: datetime,
    identifiers: dict[str, str],
    *,
    level: str | None = "INFO",
    message: str = "processed",
    attributes: dict | None = None,
) -> Event:
    return Event(
        event_id=event_id,
        timestamp=timestamp,
        service=f"service-{event_id}",
        level=level,
        message=message,
        identifiers=identifiers,
        attributes=attributes or {},
        source=EventSource(type="test", reference=event_id),
    )


def test_window_anchors_to_earliest_direct_and_filters_before_correlation():
    events = [
        make_event("direct-late", START + timedelta(minutes=5), {"transaction_id": "txn"}),
        make_event("related", START + timedelta(minutes=14), {"request_id": "req"}),
        make_event(
            "direct-early",
            START,
            {"transaction_id": "txn", "request_id": "req"},
        ),
        make_event("outside", START + timedelta(minutes=15, seconds=1), {"request_id": "req"}),
    ]

    analysis = investigate_events(events, "transaction_id", "txn")

    assert analysis.window_start == START
    assert analysis.window_end == START + timedelta(minutes=15)
    assert [item.event.event_id for item in analysis.timeline] == [
        "direct-early",
        "direct-late",
        "related",
    ]
    assert analysis.status == "no_failures_detected"


def test_reference_timestamp_overrides_earliest_direct_anchor():
    reference = START - timedelta(minutes=3)
    events = [
        make_event(
            "direct",
            START,
            {"transaction_id": "txn", "request_id": "req"},
        ),
        make_event("before-direct", reference, {"request_id": "req"}),
    ]

    analysis = investigate_events(
        events,
        "transaction_id",
        "txn",
        reference_timestamp=reference,
    )

    assert analysis.window_start == reference
    assert [item.event.event_id for item in analysis.timeline] == [
        "before-direct",
        "direct",
    ]


@pytest.mark.parametrize(
    ("level", "message", "attributes", "expected_evidence"),
    [
        ("ERROR", "failed", {}, "severity=ERROR"),
        ("fatal", "failed", {}, "severity=FATAL"),
        ("INFO", "received HTTP error", {"http.status_code": 503}, "HTTP 5xx"),
        ("INFO", "upstream response", {"status": 503}, "HTTP 5xx"),
        ("INFO", "received HTTP 504", {}, "message contains HTTP 504"),
        ("INFO", "request ended", {"result": "failure"}, "result=failure"),
        ("INFO", "request timed out", {}, "timeout indicator"),
        ("INFO", "request ended", {"success": False}, "success=false"),
        ("INFO", "request ended", {"timeout": True}, "timeout=True"),
    ],
)
def test_failure_indicators_are_reported_with_evidence(
    level: str,
    message: str,
    attributes: dict,
    expected_evidence: str,
):
    root = make_event(
        "root",
        START,
        {"transaction_id": "txn", "request_id": "req"},
    )
    failure = make_event(
        "failure",
        START + timedelta(seconds=1),
        {"request_id": "req"},
        level=level,
        message=message,
        attributes=attributes,
    )

    analysis = investigate_events([root, failure], "transaction_id", "txn")

    assert analysis.status == "failures_detected"
    assert analysis.findings[0].event_id == "failure"
    assert any(expected_evidence in item for item in analysis.findings[0].evidence)
    assert "root cause is unknown" in analysis.summary


def test_timeline_ties_use_event_id_and_summary_is_deterministic():
    events = [
        make_event("z-event", START, {"transaction_id": "txn"}),
        make_event("a-event", START, {"transaction_id": "txn"}),
    ]

    analysis = investigate_events(events, "transaction_id", "txn")

    assert [item.event.event_id for item in analysis.timeline] == ["a-event", "z-event"]
    assert analysis.summary == (
        "Found 2 correlated event(s) with no detected failure indicators; "
        "root cause is unknown."
    )


def test_no_match_has_unknown_cause_and_no_effective_start():
    analysis = investigate_events([], "transaction_id", "missing")

    assert analysis.status == "no_events"
    assert analysis.window_start is None
    assert analysis.window_end is None
    assert "no failure or cause can be determined" in analysis.summary


def test_event_limit_marks_investigation_incomplete():
    events = [
        make_event(f"event-{index:03}", START, {"transaction_id": "txn"})
        for index in range(501)
    ]

    analysis = investigate_events(events, "transaction_id", "txn")

    assert len(analysis.timeline) == 500
    assert analysis.correlation.truncated is True
    assert analysis.status == "incomplete"
    assert "root cause is unknown" in analysis.summary


def test_invalid_window_and_naive_reference_are_rejected():
    with pytest.raises(ValueError, match="window_minutes"):
        investigate_events([], "transaction_id", "txn", window_minutes=0)

    with pytest.raises(ValueError, match="timezone"):
        investigate_events(
            [],
            "transaction_id",
            "txn",
            reference_timestamp=datetime(2026, 10, 28, 10, 15),
        )
