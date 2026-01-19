from eviction_policy import LRUEvictionPolicy
from serializer import PickleSerializer, JsonSerializer

from .registry import register_eviction_policy, register_serializer

# Register Eviction Policies
register_eviction_policy("lru", LRUEvictionPolicy)

# Register Serializers
register_serializer("pickle", PickleSerializer)
register_serializer("json", JsonSerializer)
