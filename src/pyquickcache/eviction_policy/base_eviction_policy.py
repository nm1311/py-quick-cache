from abc import ABC, abstractmethod
from collections import OrderedDict


class BaseEvictionPolicy(ABC):
    """
    Strategy interface for cache eviction policies.
    Implementations (FIFO, LRU, LFU, etc.) receive lifecycle callbacks
    from the cache and decide which key to evict when capacity is exceeded.
    NOTE:
    - Policies must NOT change cache size directly.
    - Eviction occurs only via `select_eviction_key`.
    - Don't forget to register these in defaults.py
    """

    @abstractmethod
    def on_add(self, cache: OrderedDict, key: str) -> None:
        """
        Called when a new key is inserted into the cache.
        This is triggered only when the key did not previously exist
        (or was expired and removed).
        """
        pass

    @abstractmethod
    def on_update(self, cache: OrderedDict, key: str) -> None:
        """
        Called when an existing, valid key's value is updated.
        This is NOT called for new insertions.
        """
        pass

    @abstractmethod
    def on_access(self, cache: OrderedDict, key: str) -> None:
        """
        Called when a key is successfully accessed (read).
        """
        pass

    @abstractmethod
    def on_delete(self, cache: OrderedDict, key: str) -> None:
        """
        Called when a key is explicitly removed from the cache.
        This does NOT include automatic removals due to eviction
        or expiration unless explicitly invoked by the cache.
        """
        pass

    @abstractmethod
    def select_eviction_key(self, cache: OrderedDict) -> str:
        """
        Selects and returns the key that should be evicted
        when the cache exceeds its capacity.
        The cache itself is NOT modified here.
        """
        pass
