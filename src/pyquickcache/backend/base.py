from abc import ABC, abstractmethod
from typing import Any, Optional, Iterable, Dict


class BaseCacheBackend(ABC):
    """Abstract base class for cache storage backends.

    A cache backend is responsible for storage and key-level expiration mechanics, but not eviction policies or cache semantics.
    It does not implement eviction policies, metrics, logging, or public API
    semantics.

    This interface is designed to support multiple backend implementations
    such as:
        - In-memory
        - Filesystem
        - Redis / Memcached
        - Remote cache services

    All backend implementations must be synchronous and thread-safe unless
    explicitly documented otherwise.
    """

    # ─────────────────────────
    # Core key-value operations
    # ─────────────────────────

    @abstractmethod
    def get(self, key: str) -> Any:
        """Retrieve the value associated with a key.

        Args:
            key (str): The cache key to retrieve.

        Returns:
            Any: The stored value for the key.

        Raises:
            KeyNotFound: If the key does not exist.
            KeyExpired: If the key exists but has expired.
        """
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl: int) -> None:
        """Set a value for a key, overwriting any existing value.

        Args:
            key (str): The cache key to set.
            value (Any): The value to store.
            ttl (Optional[int]): Time-to-live in seconds. If None, the key
                does not expire.

        Returns:
            None
        """
        pass

    @abstractmethod
    def add(self, key: str, value: Any, ttl: int) -> None:
        """Add a value for a key only if the key does not already exist.

        Args:
            key (str): The cache key to add.
            value (Any): The value to store.
            ttl (Optional[int]): Time-to-live in seconds.

        Raises:
            KeyAlreadyExists: If the key already exists.

        Returns:
            None
        """
        pass

    @abstractmethod
    def update(self, key: str, value: Any, ttl: int) -> None:
        """Update the value of an existing key.

        Args:
            key (str): The cache key to update.
            value (Any): The new value.
            ttl (Optional[int]): Optional new TTL in seconds.

        Raises:
            KeyNotFound: If the key does not exist.

        Returns:
            None
        """
        pass

    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete a key from the backend.

        Args:
            key (str): The cache key to delete.

        Raises:
            KeyNotFound: If the key does not exist.

        Returns:
            None
        """
        pass

    @abstractmethod
    def clear(self) -> None:
        """Remove all keys and values from the backend.

        Returns:
            None
        """
        pass

    @abstractmethod
    def contains(self, key: str) -> bool:
        """Check whether a key exists in the backend.

        Args:
            key (str): The cache key to check.

        Returns:
            bool: True if the key exists, False otherwise.
        """
        pass

    def purge_expired(self) -> int:
        """
        Optional: Remove expired keys from the cache and return how many were removed.

        Returns:
            int: Number of keys removed.
        """
        return 0  # Some backends override, others can leave default
