from abc import ABC, abstractmethod
from typing import Iterable


class IntrospectionMixin(ABC):
    """
    Mixin that provides inspection and memory introspection capabilities for cache backends.

    Methods allow retrieval of current keys, total keys, size, and memory usage.
    """

    @abstractmethod
    def size(self) -> int:
        """
        Return the number of valid keys currently in the cache.

        Returns:
            int: Count of valid keys.
        """
        pass

    @abstractmethod
    def keys(self) -> Iterable[str]:
        """
        Return a list of valid keys currently in the cache.

        Returns:
            Iterable[str]: List of valid keys.
        """
        pass

    @abstractmethod
    def all_size(self) -> int:
        """
        Return the total number of keys currently in the store, including expired.

        Returns:
            int: Count of all keys.
        """
        pass

    @abstractmethod
    def all_keys(self) -> Iterable[str]:
        """
        Return a list of all keys in the store, including expired.

        Returns:
            Iterable[str]: List of all keys.
        """
        pass

    def memory_usage(self) -> int:
        """
        Return approximate memory usage of the cache in bytes.

        Includes keys, CacheEntry objects, values, TTLs, and expiration times.

        Returns:
            int: Memory usage in bytes.
        """
        pass
