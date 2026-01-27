from .base_eviction_policy import BaseEvictionPolicy
from .lru import LRUEvictionPolicy
from .fifo import FIFOEvictionPolicy
from .lfu import LFUEvictionPolicy

# Optional: define __all__ to control what 'from eviction_policy import *' does
__all__ = [
    "BaseEvictionPolicy",
    "LRUEvictionPolicy",
    "FIFOEvictionPolicy",
    "LFUEvictionPolicy",
]
