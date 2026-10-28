from abc import ABC, abstractmethod
from app.models.event import Event


class EventSourceAdapter(ABC):
    @abstractmethod
    def fetch(self, identifier_type: str, identifier_value: str) -> list[Event]:
        """Retrieve events directly matching an identifier."""
        raise NotImplementedError
