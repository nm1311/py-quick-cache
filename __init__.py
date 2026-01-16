from .cache import InMemoryCache
from .config import CacheConfig
from .registry import register_eviction_policy, register_serializer

# Load defaults on package import
from . import default_registries
