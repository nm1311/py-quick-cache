from abc import ABC, abstractmethod
from typing import Any


class BaseSerializer(ABC):
    """
    The Strategy Interface.
    Every new serializer (pickle, json, protobuff) must implement these methods.

    Don't forget to register these in defaults.py
    """

    @property
    @abstractmethod
    def extension(self) -> str:
        """The file extension for this format (e.g., 'json', 'pkl')."""
        pass

    @property
    @abstractmethod
    def is_binary(self) -> bool:
        """Returns True if the format requires binary I/O (bytes)."""
        pass

    @abstractmethod
    def serialize(self, data: Any) -> str | bytes:
        pass

    @abstractmethod
    def deserialize(self, data: str | bytes) -> Any:
        pass
