from .cache import QuickCache
from .config import QuickCacheConfig
from .registry.registry import register_eviction_policy, register_serializer

# Load defaults on package import
from .registry import default_registries

__all__ = ["QuickCache"]
