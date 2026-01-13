from abc import ABC, abstractmethod
from collections import OrderedDict

class EvictionPolicy(ABC):
    """
    The Strategy Interface. 
    Every new policy (LRU, LFU, FIFO) must implement these methods.
    """

    @abstractmethod
    def on_access(self, cache:OrderedDict, key:str):
        """Called whenever a key is retrieved (GET)."""
        pass

    @abstractmethod
    def on_update(self, cache:OrderedDict, key:str):
        "Called whenever a key is added or updated (ADD/UPDATE)."
        pass

    @abstractmethod
    def select_eviction_key(self, cache:OrderedDict) -> str:
        """Decides which key to remove when the cache is full."""
        pass


class LRUEvictionPolicy(EvictionPolicy):
    """
    Least Recently Used (LRU) Eviction Policy.
    Evicts the least recently accessed item when the cache is full.
    """

    def on_access(self, cache:OrderedDict, key:str):
        # Move the accessed key to the end to mark it as recently used
        if key in cache:
            cache.move_to_end(key)

    def on_update(self, cache:OrderedDict, key:str):
        # Move the updated key to the end to mark it as recently used
        if key in cache:
            cache.move_to_end(key)

    def select_eviction_key(self, cache:OrderedDict) -> str:
        # The first key in the OrderedDict is the least recently used
        return next(iter(cache))