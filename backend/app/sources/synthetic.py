import json
from pathlib import Path

from app.models.event import Event
from app.sources.base import EventSourceAdapter


class SyntheticSource(EventSourceAdapter):
    def __init__(self, fixture_path: Path):
        self.fixture_path = fixture_path

    def fetch(self, identifier_type: str, identifier_value: str) -> list[Event]:
        return [
            event
            for event in self.fetch_all()
            if event.identifiers.get(identifier_type) == identifier_value
        ]

    def fetch_all(self) -> list[Event]:
        raw = json.loads(self.fixture_path.read_text(encoding="utf-8"))
        return [Event.model_validate(item) for item in raw]
