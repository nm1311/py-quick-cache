from typing import Any
import pickle

from .base_serializer import BaseSerializer

# from ..registry.decorators import register_serializer


# @register_serializer("pickle")
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
