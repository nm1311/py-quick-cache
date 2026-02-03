from abc import ABC, abstractmethod
from typing import Iterable, Dict, Any


class BulkOperationsMixin(ABC):
    """
    Mixin that provides bulk operations for cache backends.

    Provides methods to get, set, and delete multiple keys in one call.
    """

    @abstractmethod
    def get_many(self, keys: Iterable[str]) -> Dict[str, Any]:
        """
        Retrieve multiple keys from the cache.

        Args:
            keys (Iterable[str]): Keys to retrieve.

        Returns:
            Dict[str, Any]: Mapping of key to value for valid keys.
        """
        pass

    @abstractmethod
    def set_many(self, mapping: Dict[str, Any], ttl: int) -> None:
        """
        Set multiple key-value pairs in the cache with the same TTL.

        Args:
            mapping (Dict[str, Any]): Key-value pairs to set.
            ttl (int): Time-to-live for all keys in seconds.
        """
        pass

    @abstractmethod
    def delete_many(self, keys: Iterable[str]) -> None:
        """
        Delete multiple keys from the cache.

        Args:
            keys (Iterable[str]): Keys to delete.
        """
        pass
