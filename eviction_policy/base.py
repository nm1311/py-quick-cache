from abc import ABC, abstractmethod
from collections import OrderedDict


class EvictionPolicy(ABC):
    """
    The Strategy Interface.
    Every new policy (LRU, LFU, FIFO) must implement these methods.

    Don't forget to register these in defaults.py
    """

    @abstractmethod
    def on_access(self, cache: OrderedDict, key: str):
        """Called whenever a key is retrieved (GET)."""
        pass

    @abstractmethod
    def on_update(self, cache: OrderedDict, key: str):
        "Called whenever a key is added or updated (ADD/UPDATE)."
        pass

    @abstractmethod
    def select_eviction_key(self, cache: OrderedDict) -> str:
        """Decides which key to remove when the cache is full."""
        pass
