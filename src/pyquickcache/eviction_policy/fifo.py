from collections import OrderedDict
from .base_eviction_policy import BaseEvictionPolicy

# from ..registry.decorators import register_eviction_policy


# @register_eviction_policy("fifo")
class FIFOEvictionPolicy(BaseEvictionPolicy):
    """
    First In First Out (FIFO) Eviction Policy.
    Evicts the oldest inserted item when the cache is full.
    """

    def on_add(self, cache, key) -> None:
        """
        Move newly added key to the end to preserve insertion order
        """
        if key in cache:
            cache.move_to_end(key)

    def on_update(self, cache: OrderedDict, key: str) -> None:
        """Do Nothing"""
        pass

    def on_access(self, cache: OrderedDict, key: str) -> None:
        """Do Nothing"""
        pass

    def on_delete(self, cache, key) -> None:
        """Do Nothing"""
        pass

    def select_eviction_key(self, cache: OrderedDict) -> str:
        """The first key in the OrderedDict is the least recently used"""
        if not cache:
            raise RuntimeError("Eviction requested on empty cache")
        return next(iter(cache))
