from collections import OrderedDict
from .base import EvictionPolicy


class LRUEvictionPolicy(EvictionPolicy):
    """
    Least Recently Used (LRU) Eviction Policy.
    Evicts the least recently accessed item when the cache is full.
    """

    def on_access(self, cache: OrderedDict, key: str):
        # Move the accessed key to the end to mark it as recently used
        if key in cache:
            cache.move_to_end(key)

    def on_update(self, cache: OrderedDict, key: str):
        # Move the updated key to the end to mark it as recently used
        if key in cache:
            cache.move_to_end(key)

    def select_eviction_key(self, cache: OrderedDict) -> str:
        # The first key in the OrderedDict is the least recently used
        return next(iter(cache))
