import pytest
from pydantic import ValidationError
from app.models.event import Event


def test_timezone_required():
    with pytest.raises(ValidationError):
        Event.model_validate({"event_id": "e1", "timestamp": "2026-10-28T10:00:00", "service": "api", "message": "test", "source": {"type": "synthetic", "reference": "fixture"}})


def test_optional_fields_default_to_empty():
    event = Event.model_validate({"event_id": "e1", "timestamp": "2026-10-28T10:00:00Z", "service": "api", "message": "test", "source": {"type": "synthetic", "reference": "fixture"}})
    assert event.identifiers == {}
    assert event.attributes == {}
