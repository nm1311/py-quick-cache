from abc import ABC, abstractmethod
from typing import Any
import pickle

class BaseSerializer(ABC):

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


class PickleSerializer(BaseSerializer):

    @property
    def extension(self) -> str:
        return "pkl"
    @property
    def is_binary(self) -> bool:
        return True

    def serialize(self, data: Any) -> str | bytes:
        return pickle.dumps(data)

    def deserialize(self, data: str | bytes) -> Any:
        return pickle.loads(data)