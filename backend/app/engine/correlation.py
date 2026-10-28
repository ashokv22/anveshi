from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime

from app.core.constants import (
    DEFAULT_MAX_CORRELATED_EVENTS,
    DEFAULT_MAX_CORRELATION_DEPTH,
    SAFE_CORRELATION_IDENTIFIER_KEYS,
)
from app.models.event import Event


@dataclass(frozen=True)
class CorrelatedEvent:
    event: Event
    correlation_type: str
    depth: int
    parent_event_id: str | None
    matched_identifier_key: str
    matched_identifier_value: str


@dataclass(frozen=True)
class CorrelationResult:
    events: list[CorrelatedEvent]
    truncated: bool
    direct_count: int
    discovered_count: int
    depth_reached: int


def _event_order(event: Event) -> tuple[datetime, str]:
    return event.timestamp, event.event_id


def correlate(
    events: list[Event],
    identifier_key: str,
    identifier_value: str,
    max_depth: int = DEFAULT_MAX_CORRELATION_DEPTH,
    max_events: int = DEFAULT_MAX_CORRELATED_EVENTS,
) -> CorrelationResult:
    if (
        not isinstance(identifier_key, str)
        or not identifier_key.strip()
        or not isinstance(identifier_value, str)
        or not identifier_value.strip()
    ):
        raise ValueError("Identifier key and value are required")
    if not isinstance(max_depth, int) or isinstance(max_depth, bool) or max_depth < 0:
        raise ValueError("max_depth must be a non-negative integer")
    if not isinstance(max_events, int) or isinstance(max_events, bool) or max_events < 1:
        raise ValueError("max_events must be a positive integer")

    unique_events: dict[str, Event] = {}
    for event in events:
        existing = unique_events.get(event.event_id)
        if existing is not None and existing != event:
            raise ValueError(f"Conflicting records share event_id {event.event_id!r}")
        unique_events[event.event_id] = event

    identifier_index: dict[tuple[str, str], list[Event]] = defaultdict(list)
    for event in unique_events.values():
        for key, value in event.identifiers.items():
            if key and value:
                identifier_index[(key, value)].append(event)
    for candidates in identifier_index.values():
        candidates.sort(key=_event_order)

    direct_matches = identifier_index.get((identifier_key, identifier_value), [])
    correlated: list[CorrelatedEvent] = []
    visited: set[str] = set()
    queue: deque[CorrelatedEvent] = deque()
    truncated = False

    for event in direct_matches:
        if len(correlated) == max_events:
            truncated = True
            break
        visited.add(event.event_id)
        result = CorrelatedEvent(
            event=event,
            correlation_type="direct",
            depth=0,
            parent_event_id=None,
            matched_identifier_key=identifier_key,
            matched_identifier_value=identifier_value,
        )
        correlated.append(result)
        queue.append(result)

    while queue:
        current = queue.popleft()
        if current.depth >= max_depth:
            continue

        for key, value in sorted(current.event.identifiers.items()):
            if (
                not key
                or not value
                or key not in SAFE_CORRELATION_IDENTIFIER_KEYS
                or (key, value) == (identifier_key, identifier_value)
            ):
                continue

            for candidate in identifier_index.get((key, value), []):
                if candidate.event_id in visited:
                    continue
                if len(correlated) == max_events:
                    truncated = True
                    queue.clear()
                    break

                visited.add(candidate.event_id)
                result = CorrelatedEvent(
                    event=candidate,
                    correlation_type="discovered",
                    depth=current.depth + 1,
                    parent_event_id=current.event.event_id,
                    matched_identifier_key=key,
                    matched_identifier_value=value,
                )
                correlated.append(result)
                queue.append(result)
            if truncated:
                break

    return CorrelationResult(
        events=correlated,
        truncated=truncated,
        direct_count=sum(item.correlation_type == "direct" for item in correlated),
        discovered_count=sum(
            item.correlation_type == "discovered" for item in correlated
        ),
        depth_reached=max((item.depth for item in correlated), default=0),
    )
