from collections import OrderedDict
from .base_eviction_policy import BaseEvictionPolicy

# from ..registry.decorators import register_eviction_policy


# @register_eviction_policy("lru")
class LRUEvictionPolicy(BaseEvictionPolicy):
    """
    Least Recently Used (LRU) Eviction Policy.
    Evicts the least recently accessed item when the cache is full.
    """

    def on_add(self, cache, key) -> None:
        """Move the updated key to the end to mark it as recently used"""
        if key in cache:
            cache.move_to_end(key)

    def on_update(self, cache: OrderedDict, key: str) -> None:
        """Move the updated key to the end to mark it as recently used"""
        if key in cache:
            cache.move_to_end(key)

    def on_access(self, cache: OrderedDict, key: str) -> None:
        """Move the accessed key to the end to mark it as recently used"""
        if key in cache:
            cache.move_to_end(key)

    def on_delete(self, cache, key) -> None:
        """Do Nothing"""
        pass

    def select_eviction_key(self, cache: OrderedDict) -> str:
        """The first key in the OrderedDict is the least recently used"""
        if not cache:
            raise RuntimeError("Eviction requested on empty cache")
        return next(iter(cache))
