from datetime import datetime, timezone

import pytest

from app.engine.correlation import CorrelationResult, correlate
from app.models.event import Event, EventSource


def make_event(
    event_id: str,
    identifiers: dict[str, str],
    *,
    second: int = 0,
    message: str | None = None,
) -> Event:
    return Event(
        event_id=event_id,
        timestamp=datetime(2026, 10, 28, 10, 15, second, tzinfo=timezone.utc),
        service="test-service",
        message=message or event_id,
        identifiers=identifiers,
        source=EventSource(type="test", reference=event_id),
    )


def test_correlates_multiple_hops_with_discovery_evidence():
    events = [
        make_event("A", {"transaction_id": "txn-1", "request_id": "req-1"}),
        make_event("B", {"request_id": "req-1", "trace_id": "trace-1"}),
        make_event("C", {"trace_id": "trace-1"}),
        make_event("unrelated", {"request_id": "req-999"}),
    ]

    result = correlate(events, "transaction_id", "txn-1")

    assert [item.event.event_id for item in result.events] == ["A", "B", "C"]
    assert [(item.correlation_type, item.depth) for item in result.events] == [
        ("direct", 0),
        ("discovered", 1),
        ("discovered", 2),
    ]
    assert result.events[1].parent_event_id == "A"
    assert result.events[1].matched_identifier_key == "request_id"
    assert result.events[1].matched_identifier_value == "req-1"
    assert result.events[2].parent_event_id == "B"
    assert result.truncated is False


def test_cycles_and_duplicate_identical_records_are_deduplicated():
    a = make_event("A", {"transaction_id": "txn-1", "request_id": "req-1"})
    b = make_event("B", {"request_id": "req-1", "trace_id": "trace-1"})
    c = make_event("C", {"trace_id": "trace-1", "request_id": "req-1"})

    result = correlate([c, b, a, a], "transaction_id", "txn-1")

    assert [item.event.event_id for item in result.events] == ["A", "B", "C"]


def test_results_are_deterministic_regardless_of_input_order():
    events = [
        make_event("root-b", {"transaction_id": "txn-1"}, second=1),
        make_event("root-a", {"transaction_id": "txn-1"}, second=1),
        make_event("child-b", {"request_id": "req-1"}, second=3),
        make_event("child-a", {"request_id": "req-1"}, second=2),
        make_event("bridge", {"transaction_id": "txn-1", "request_id": "req-1"}),
    ]

    forward = correlate(events, "transaction_id", "txn-1")
    reverse = correlate(list(reversed(events)), "transaction_id", "txn-1")

    assert [
        (item.event.event_id, item.parent_event_id, item.depth)
        for item in forward.events
    ] == [
        (item.event.event_id, item.parent_event_id, item.depth)
        for item in reverse.events
    ]


def test_depth_limit_stops_expansion():
    events = [
        make_event("A", {"transaction_id": "txn-1", "request_id": "req-1"}),
        make_event("B", {"request_id": "req-1", "trace_id": "trace-1"}),
        make_event("C", {"trace_id": "trace-1"}),
    ]

    result = correlate(events, "transaction_id", "txn-1", max_depth=1)

    assert [item.event.event_id for item in result.events] == ["A", "B"]
    assert result.depth_reached == 1


def test_event_limit_reports_truncation_only_if_more_events_match():
    events = [
        make_event("A", {"transaction_id": "txn-1", "request_id": "req-1"}),
        make_event("B", {"request_id": "req-1"}),
        make_event("C", {"request_id": "req-1"}),
    ]

    result = correlate(events, "transaction_id", "txn-1", max_events=2)
    exact_limit = correlate(events[:2], "transaction_id", "txn-1", max_events=2)

    assert [item.event.event_id for item in result.events] == ["A", "B"]
    assert result.truncated is True
    assert exact_limit.truncated is False


def test_empty_result_and_unsafe_identifier_bridges():
    events = [
        make_event("A", {"transaction_id": "txn-1", "user_id": "user-1"}),
        make_event("B", {"user_id": "user-1", "session_id": "session-1"}),
        make_event("C", {"session_id": "session-1"}),
    ]

    result = correlate(events, "transaction_id", "txn-1")
    empty = correlate(events, "transaction_id", "missing")

    assert [item.event.event_id for item in result.events] == ["A"]
    assert empty == CorrelationResult([], False, 0, 0, 0)


def test_conflicting_duplicate_event_ids_are_reported():
    original = make_event("same", {"transaction_id": "txn-1"})
    conflict = make_event(
        "same",
        {"transaction_id": "txn-1"},
        message="different record",
    )

    with pytest.raises(ValueError, match="Conflicting records share event_id"):
        correlate([original, conflict], "transaction_id", "txn-1")


@pytest.mark.parametrize(
    ("identifier_key", "identifier_value", "max_depth", "max_events"),
    [
        ("", "value", 2, 500),
        ("key", " ", 2, 500),
        ("key", "value", -1, 500),
        ("key", "value", 2, 0),
    ],
)
def test_invalid_arguments_are_rejected(
    identifier_key: str,
    identifier_value: str,
    max_depth: int,
    max_events: int,
):
    with pytest.raises(ValueError):
        correlate([], identifier_key, identifier_value, max_depth, max_events)
