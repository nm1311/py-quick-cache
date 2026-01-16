from typing import Any
import pickle

from .base import BaseSerializer


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
