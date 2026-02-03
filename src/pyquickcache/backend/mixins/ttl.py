from abc import ABC, abstractmethod
from typing import Optional


class TTLManagementMixin(ABC):
    """
    Mixin that provides TTL inspection and modification methods for cache backends.
    """

    @abstractmethod
    def ttl(self, key: str) -> int:
        """
        Return the remaining TTL of a key in seconds.

        Args:
            key (str): The key to inspect.

        Returns:
            int: Remaining TTL in seconds.

        Raises:
            KeyNotFound: If the key does not exist.
            KeyExpired: If the key has expired.
        """
        pass

    @abstractmethod
    def expire(self, key: str, ttl: int) -> None:
        """
        Set a new TTL for an existing key.

        Args:
            key (str): Key to update.
            ttl (int): New TTL in seconds.

        Raises:
            KeyNotFound: If the key does not exist.
            KeyExpired: If the key has already expired.
        """
        pass
