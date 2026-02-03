from collections import OrderedDict
from datetime import timedelta
from threading import RLock
from typing import Any, Iterable, Dict
from enum import Enum, auto
import sys

from ..utils.helpers import utcnow
from .base import BaseCacheBackend
from .mixins import (
    BulkOperationsMixin,
    TTLManagementMixin,
    IntrospectionMixin,
    LifecycleMixin,
)
from ..exceptions import KeyExpired, KeyNotFound, KeyAlreadyExists

from ._cache_entry import CacheEntry

from ..registry.decorators import register_cache_backend

class KeyStatus(Enum):
    """Internal enum representing the state of a cache key."""

    MISSING = auto()
    EXPIRED = auto()
    VALID = auto()

@register_cache_backend("inmemory")
class InMemoryBackend(
    BaseCacheBackend,
    BulkOperationsMixin,
    TTLManagementMixin,
    IntrospectionMixin,
    LifecycleMixin,
):
    """
    In-memory cache backend implementing all core cache operations.

    Provides thread-safe storage with TTL management, bulk operations,
    introspection, memory usage calculation, and optional lifecycle management.
    """

    def __init__(self):
        """Initialize the in-memory store and lock."""
        self._store: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = RLock()

    # -------------------------
    # Core Operations
    # -------------------------

    def get(self, key: str) -> CacheEntry:
        """
        Retrieve the cache entry for a key.

        Raises:
            KeyNotFound: If the key does not exist.
            KeyExpired: If the key has expired.
        """
        with self._lock:
            key_status = self._inspect_key(key=key)
            if key_status is KeyStatus.MISSING:
                raise KeyNotFound(key=key)

            if key_status is KeyStatus.EXPIRED:
                raise KeyExpired(key=key)

            return self._store[key]

    def set(self, key: str, value: Any, ttl: int) -> None:
        """Set or overwrite a key in the cache with a TTL."""
        with self._lock:
            entry = self._build_entry(value=value, ttl=ttl)
            self._write_entry(key=key, entry=entry)

    def add(self, key: str, value: Any, ttl: int) -> None:
        """
        Add a key only if it does not exist or is expired.

        Raises:
            KeyAlreadyExists: If the key is valid in cache.
        """
        with self._lock:
            key_status = self._inspect_key(key=key)

            if key_status is KeyStatus.VALID:
                raise KeyAlreadyExists(key=key)

            if key_status is KeyStatus.EXPIRED:
                self._store.pop(key)

            entry = self._build_entry(value=value, ttl=ttl)
            self._write_entry(key=key, entry=entry)

    def update(self, key: str, value: Any, ttl: int) -> None:
        """
        Update the value and TTL of an existing key.

        Raises:
            KeyNotFound: If the key does not exist.
            KeyExpired: If the key has expired.
        """
        with self._lock:
            key_status = self._inspect_key(key=key)

            if key_status is KeyStatus.MISSING:
                raise KeyNotFound(key=key)

            if key_status is KeyStatus.EXPIRED:
                self._store.pop(key)
                raise KeyExpired(key=key)

            new_entry = self._build_entry(value=value, ttl=ttl)
            self._write_entry(key=key, entry=new_entry)

    def delete(self, key: str) -> None:
        """
        Delete a key from the cache.

        Raises:
            KeyNotFound: If the key does not exist.
            KeyExpired: If the key has expired.
        """
        with self._lock:
            key_status = self._inspect_key(key=key)

            if key_status is KeyStatus.MISSING:
                raise KeyNotFound(key=key)

            if key_status is KeyStatus.EXPIRED:
                raise KeyExpired(key=key)

            self._store.pop(key)

    def clear(self) -> None:
        """Remove all keys from the cache."""
        with self._lock:
            self._store.clear()

    def contains(self, key: str) -> bool:
        """Check if a key exists and is valid in the cache."""
        with self._lock:
            key_status = self._inspect_key(key=key)

            if (key_status is KeyStatus.MISSING) or (key_status is KeyStatus.EXPIRED):
                return False

            return True

    def purge_expired(self) -> int:
        """Remove all expired keys and return how many were removed."""
        removed = 0
        with self._lock:
            for key in self._store.keys():
                key_status = self._inspect_key(key=key)
                if key_status is KeyStatus.EXPIRED:
                    removed = removed + 1
        return removed

    # -------------------------
    # Bulk Operations Mixin
    # -------------------------

    def get_many(self, keys: Iterable[str]) -> Dict[str, Any]:
        """Retrieve multiple keys from the cache."""
        result: Dict[str, Any] = {}

        with self._lock:
            for key in keys:
                key_status = self._inspect_key(key=key)

                if key_status is not KeyStatus.VALID:
                    continue

                result[key] = self._store[key].value

        return result

    def set_many(self, mapping: Dict[str, Any], ttl: int) -> None:
        """Set multiple keys with the same TTL."""
        with self._lock:
            for key, value in mapping.items():
                _entry = self._build_entry(value=value, ttl=ttl)
                self._write_entry(key=key, entry=_entry)

    def delete_many(self, keys: Iterable[str]) -> None:
        """Delete multiple keys from the cache."""
        with self._lock:
            for key in keys:
                key_status = self._inspect_key(key=key)

                if key_status is KeyStatus.VALID:
                    self._store.pop(key)

    # -------------------------
    # Introspection Mixin
    # -------------------------

    def size(self) -> int:
        """Return the number of valid keys in the cache."""
        self.purge_expired()
        with self._lock:
            return len(self._store)

    def keys(self) -> Iterable[str]:
        """Return a list of valid keys in the cache."""
        self.purge_expired()
        with self._lock:
            return list(self._store.keys())

    def all_size(self) -> int:
        """Return the total number of keys in the store (including expired)."""
        with self._lock:
            return len(self._store)

    def all_keys(self) -> Iterable[str]:
        """Return all keys in the store (including expired)."""
        with self._lock:
            return list(self._store.keys())

    def memory_usage(self) -> int:
        """Return approximate memory usage in bytes, including keys, entries, values, TTLs, and expiration times."""
        total = 0
        with self._lock:
            for key, entry in self._store.items():
                total += sys.getsizeof(key)  # key size
                total += sys.getsizeof(entry)  # CacheEntry object itself
                total += sys.getsizeof(entry.value)  # actual stored value
                total += sys.getsizeof(entry.ttl)  # ttl entry
                total += sys.getsizeof(entry.expiration_time)  # expiration time
        return total

    # -------------------------
    # TTL Management Mixin
    # -------------------------

    def ttl(self, key) -> int:
        """
        Return remaining TTL in seconds.

        Raises:
            KeyNotFound: If key does not exist.
            KeyExpired: If key has expired.
        """
        with self._lock:
            key_status = self._inspect_key(key=key)
            if key_status is KeyStatus.MISSING:
                raise KeyNotFound(key=key)
            if key_status is KeyStatus.EXPIRED:
                raise KeyExpired(key=key)

            entry = self._store[key]
            remaining = (entry.expiration_time - utcnow()).total_seconds()
            return max(0, int(remaining))

    def expire(self, key, ttl):
        """
        Set a new TTL for an existing key.

        Raises:
            KeyNotFound: If key does not exist.
            KeyExpired: If key has expired.
        """
        with self._lock:
            key_status = self._inspect_key(key=key)
            if key_status is KeyStatus.MISSING:
                raise KeyNotFound(key=key)
            if key_status is KeyStatus.EXPIRED:
                raise KeyExpired(key=key)

            entry = self._store[key]
            entry.ttl = ttl
            entry.expiration_time = utcnow() + timedelta(seconds=ttl)

    # -------------------------
    # Lifecycle Mixin
    # -------------------------

    def close(self) -> None:
        """No-op for in-memory backend; backend has no external resources."""
        pass

    # -------------------------
    # Internal helper functions
    # -------------------------

    def _build_entry(self, value: Any, ttl: int) -> CacheEntry:
        """Build a CacheEntry object from a value and TTL."""
        entry = CacheEntry(
            value=value, expiration_time=utcnow() + timedelta(seconds=ttl), ttl=ttl
        )
        return entry

    def _write_entry(self, key: str, entry: CacheEntry):
        """Write a CacheEntry to the store."""
        self._store[key] = entry

    def _inspect_key(self, key: str) -> KeyStatus:
        """Check the status of a key (missing, expired, or valid)."""
        if key not in self._store:
            return KeyStatus.MISSING

        if self._store[key].is_expired():
            self._store.pop(key)
            return KeyStatus.EXPIRED

        return KeyStatus.VALID
