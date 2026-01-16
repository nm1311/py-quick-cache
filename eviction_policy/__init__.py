from .base import EvictionPolicy
from .lru import LRUEvictionPolicy

# Optional: define __all__ to control what 'from eviction_policy import *' does
__all__ = ["EvictionPolicy", "LRUEvictionPolicy"]
