from typing import Any
import json

from .base_serializer import BaseSerializer

# from ..registry.decorators import register_serializer


# @register_serializer("json")
class JsonSerializer(BaseSerializer):

    @property
    def extension(self) -> str:
        return "json"

    @property
    def is_binary(self) -> bool:
        return False

    def serialize(self, data: Any) -> str | bytes:
        return json.dumps(data, indent=4)

    def deserialize(self, data: str | bytes) -> Any:
        return json.loads(data)
