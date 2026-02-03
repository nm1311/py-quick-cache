from typing import Any, Optional
from datetime import datetime, timedelta, timezone
from collections import OrderedDict
import threading
from enum import Enum, auto
from dataclasses import dataclass
import atexit

from .base_cache import BaseCache
from .registry.registry import create_eviction_policy, create_serializer
from .quick_cache_config import QuickCacheConfig
from .storage import FileManager, FileSystemStorage
from .metrics import CacheMetrics, NoOpMetrics
from .exceptions import (
    KeyExpired,
    KeyNotFound,
    KeyAlreadyExists,
    InvalidTTL,
    CacheLoadError,
    CacheSaveError,
    CacheMetricsSaveError,
)
from .utils.helpers import utcnow

import logging

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


@dataclass(slots=True)
class CacheEntry:
    """
    INTERNAL.

    Represents a single cache entry with an absolute expiration time.

    Purpose:
        Encapsulates the cached value along with TTL metadata and a computed
        expiration timestamp.

    Invariants:
        - expiration_time is always timezone-aware (UTC)
        - ttl is the original TTL (in seconds) used to compute expiration_time

    Notes:
        This class is not part of the public API and may change without notice.
    """

    value: Any
    expiration_time: datetime
    ttl: int

    def to_dict(self) -> dict:
        """
        INTERNAL.

        Serialize this cache entry into a dictionary representation.

        Purpose:
            Used by serializers and persistence layers to convert cache entries
            into a JSON-compatible format.

        Behavior:
            - Converts expiration_time to ISO 8601 string
            - Does not perform deep serialization of the value
        """

        return {
            "value": self.value,
            "expiration_time": self.expiration_time.isoformat(),  # Handle datetime conversion here
            "ttl": self.ttl,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CacheEntry":
        """
        INTERNAL.

        Serialize this cache entry into a dictionary representation.

        Purpose:
            Used by serializers and persistence layers to convert cache entries
            into a JSON-compatible format.

        Behavior:
            - Converts expiration_time to ISO 8601 string
            - Does not perform deep serialization of the value
        """

        expiration = datetime.fromisoformat(data["expiration_time"])

        # Ensure timezone awareness as fromisoformat may return naive datetime
        if expiration.tzinfo is None:
            expiration = expiration.replace(tzinfo=timezone.utc)

        return cls(
            value=data["value"],
            expiration_time=expiration,  # Revert string to datetime
            ttl=data["ttl"],
        )

    def is_expired(self) -> bool:
        """
        INTERNAL.

        Check whether this cache entry has expired.

        Behavior:
            - Compares the current UTC time against expiration_time
            - Does not mutate cache state

        Returns:
            bool: True if the entry is expired, False otherwise.
        """

        return utcnow() > self.expiration_time


class KeyStatus(Enum):
    """
    INTERNAL.

    Represents the evaluated state of a cache key during lookup.

    Used by:
        - Internal inspection helpers
        - Public API methods to decide control flow without raising

    Values:
        MISSING:
            Key does not exist in the cache.

        EXPIRED:
            Key exists but has exceeded its TTL and was removed.

        VALID:
            Key exists and is not expired.
    """

    MISSING = auto()
    EXPIRED = auto()
    VALID = auto()


class QuickCache(BaseCache):
    """
    Thread-safe in-memory cache with TTL support, eviction policies, persistence,
    and optional metrics collection.

    QuickCache is designed for backend services and Python applications where
    fast, in-memory data access is required. It supports:

    - Time-based expiration (TTL)
    - Pluggable eviction policies (e.g., LRU, custom policies)
    - Disk persistence via configurable serializers
    - Background cleanup of expired entries
    - Optional metrics collection and persistence

    The cache exposes a Pythonic exception-based API consistent with standard
    library behavior.
    """

    def __init__(
        self,
        config: Optional[QuickCacheConfig] = None,
    ) -> None:
        """
        Initialize a new QuickCache instance.

        Args:
            config (Optional[QuickCacheConfig]): Cache configuration object.
                If not provided, default configuration values are used.

        Raises:
            ValueError: If the configured eviction policy or serializer is unknown.
        """

        # Load default config if no config is provided
        self.config = config or QuickCacheConfig()

        self.eviction_policy = create_eviction_policy(self.config.eviction_policy)
        self.serializer = create_serializer(self.config.serializer)

        self.metrics = CacheMetrics() if self.config.enable_metrics else NoOpMetrics()
        self.metrics_serializer = create_serializer(self.config.metrics_serializer)

        self.cache_file_manager = FileManager(
            default_dir=self.config.storage_dir,
            default_filename=self.config.filename,
        )

        self.cache_metrics_file_manager = FileManager(
            default_dir=self.config.metrics_storage_dir,
            default_filename=self.config.metrics_filename,
        )

        # In memory Cache
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.max_cache_size = self.config.max_size

        # The stop signal
        self._stop_event = threading.Event()
        # Start background cleanup thread (deamon=True to make sure it exits with main program)
        self._lock: threading.RLock = threading.RLock()
        # self._stop_event = threading.Event() # The "Stop Signal" in case our main program wants to exit
        self.cleanup_thread = threading.Thread(
            target=self._background_cleanup, daemon=True
        )
        self.cleanup_thread.start()

        atexit.register(self.stop)

        logger.info(
            msg="The cache and metrics have been initialized with the chosen serializers and eviltion policies."
        )

    def __repr__(self) -> str:
        return f"<QuickCache(size={self.size()}, max_size={self.max_cache_size}, policy='{self.config.eviction_policy}')>"

    def get(self, key: str) -> Any:
        """
        Retrieve the value associated with a key from the cache.

        Args:
            key (str): The cache key to retrieve.

        Returns:
            Any: The cached value.

        Raises:
            KeyNotFound: If the key does not exist.
            KeyExpired: If the key exists but has expired.
        """

        self.metrics.record_get()

        with self._lock:
            status = self._inspect_key(key)

            if status is KeyStatus.MISSING:
                self.metrics.record_miss()
                raise KeyNotFound(key=key)

            if status is KeyStatus.EXPIRED:
                self.metrics.record_miss()
                raise KeyExpired(key=key)

            # --- PLUGGABLE HOOK FOR EVICTION POLICY ---
            self.eviction_policy.on_access(self.cache, key)

            self.metrics.record_hit()
            return self.cache[key].value

    def set(self, key: str, value: Any, ttl_sec: int = None) -> None:
        """
        Insert or update a key in the cache.

        If the key already exists, its value and expiration time are updated.
        If no TTL is provided, the default TTL from configuration is used.

        Args:
            key (str): The cache key.
            value (Any): The value to store.
            ttl_sec (Optional[int]): Time-to-live in seconds.

        Raises:
            InvalidTTL: If the provided TTL is invalid.
        """

        if ttl_sec is None:
            ttl = self.config.default_ttl
        elif self._is_ttl_valid(ttl_sec):
            ttl = int(ttl_sec)
        else:
            raise InvalidTTL(ttl=ttl_sec)

        with self._lock:
            self._internal_set(key, value, ttl)

            logger.debug(f"Key '{key}' set.")

    def add(self, key: str, value: Any, ttl_sec: int = None) -> None:
        """
        Insert a key into the cache only if it does not already exist
        or if the previous entry has expired.

        Args:
            key (str): The cache key.
            value (Any): The value to store.
            ttl_sec (Optional[int]): Time-to-live in seconds.

        Raises:
            KeyAlreadyExists: If a valid key already exists.
            InvalidTTL: If the provided TTL is invalid.
        """

        with self._lock:

            if ttl_sec is None:
                ttl = self.config.default_ttl
            elif self._is_ttl_valid(ttl=ttl_sec) is True:
                ttl = int(ttl_sec)
            else:
                raise InvalidTTL(ttl=ttl_sec)

            status = self._inspect_key(key=key)

            if status is KeyStatus.VALID:
                self.metrics.record_failed_op()
                raise KeyAlreadyExists(key=key)

            # status is MISSING or EXPIRED → allowed to add
            if self.size() >= self.max_cache_size:
                self._ensure_capacity()

            # Add a new cache entry as no valid key exists
            self.cache[key] = CacheEntry(
                value=value,
                expiration_time=utcnow() + timedelta(seconds=ttl),
                ttl=ttl,
            )

            logger.debug(f"Key '{key}' added.")

            # SYNC THE METRICS
            # Record a successful set operation and update the total keys as well as valid keys since we know one more valid key is added
            self.metrics.record_set()
            self.metrics.update_total_keys(self.size())
            self.metrics.update_valid_keys_by_delta(delta=1)

            # --- PLUGGABLE HOOK FOR EVICTION POLICY ---
            self.eviction_policy.on_add(self.cache, key)

    def update(self, key: str, value: Any, ttl_sec: int = None) -> None:
        """
        Update the value of an existing valid key.

        Args:
            key (str): The cache key.
            value (Any): The new value.
            ttl_sec (Optional[int]): Time-to-live in seconds.

        Raises:
            KeyNotFound: If the key does not exist.
            KeyExpired: If the key exists but has expired.
            InvalidTTL: If the provided TTL is invalid.
        """

        with self._lock:

            if ttl_sec is None:
                ttl = self.config.default_ttl
            elif self._is_ttl_valid(ttl=ttl_sec) is True:
                ttl = int(ttl_sec)
            else:
                raise InvalidTTL(ttl=ttl_sec)

            status = self._inspect_key(key=key)

            if status is KeyStatus.MISSING:
                self.metrics.record_failed_op()
                raise KeyNotFound(key=key)

            if status is KeyStatus.EXPIRED:
                self.metrics.record_failed_op()
                raise KeyExpired(key=key)

            # Perform the update, as a valid key is present
            self.cache[key] = CacheEntry(
                value=value,
                expiration_time=utcnow() + timedelta(seconds=ttl),
                ttl=ttl,
            )

            logger.debug(f"Key '{key}' updated.")

            # --- PLUGGABLE HOOK FOR EVICTION POLICY ---
            self.eviction_policy.on_update(self.cache, key)

            # SYNC THE METRICS
            # Record a successful set and update the total and valid keys
            self.metrics.record_set()
            self.metrics.update_total_keys(self.size())
            # self.metrics.update_valid_keys_by_delta(delta=0)

    def delete(self, key: str) -> None:
        """
        Remove a key from the cache.

        Args:
            key (str): The cache key to delete.

        Raises:
            KeyNotFound: If the key does not exist.
            KeyExpired: If the key exists but has expired.
        """

        with self._lock:
            status = self._inspect_key(key=key)

            if status is KeyStatus.MISSING:
                self.metrics.record_miss()
                raise KeyNotFound(key=key)

            if status is KeyStatus.EXPIRED:
                self.metrics.record_miss()
                raise KeyExpired(key=key)

            # Delete the valid key
            self.cache.pop(key)

            # Eviction Policy Hook
            self.eviction_policy.on_delete(self.cache, key)

            logger.debug(f"Key '{key}' manually deleted.")

            # SYNC THE METRICS
            # Record manual deletion, and update the total and valid keys accordingly
            self.metrics.record_manual_deletion()
            self.metrics.update_total_keys(self.size())
            self.metrics.update_valid_keys_by_delta(delta=-1)

    def set_many(self, data: dict[str, Any], ttl_sec: int = None) -> None:
        """
        Insert or update multiple keys in a single operation.

        Each key is treated as an independent set operation for metrics
        and eviction handling.

        Args:
            data (dict[str, Any]): Mapping of keys to values.
            ttl_sec (Optional[int]): Time-to-live in seconds.

        Raises:
            InvalidTTL: If the provided TTL is invalid.
        """

        if ttl_sec is None:
            ttl = self.config.default_ttl
        elif self._is_ttl_valid(ttl=ttl_sec) is True:
            ttl = int(ttl_sec)
        else:
            raise InvalidTTL(ttl=ttl_sec)

        with self._lock:
            for key, value in data.items():
                # We use the internal method that doesn't care about missing or expired keys
                self._internal_set(key, value, ttl)

    def get_many(self, keys: list[str]) -> dict[str, Any]:
        """
        Retrieve multiple keys from the cache.

        Missing or expired keys are skipped. Only valid keys are returned.

        Args:
            keys (list[str]): List of cache keys.

        Returns:
            dict[str, Any]: Mapping of valid keys to their values.
        """
        results = {}

        with self._lock:
            # Record only the overall bulk operation
            self.metrics.record_get()

            for key in keys:
                status = self._inspect_key(key=key)

                if status is KeyStatus.VALID:
                    results[key] = self.cache[key].value
                    self.metrics.record_hit()
                    # Eviction policy hook
                    self.eviction_policy.on_access(self.cache, key)
                else:
                    # Missing or expired keys: record a miss
                    self.metrics.record_miss()

        return results

    def delete_many(self, keys: list[str]) -> None:
        """
        Delete multiple keys from the cache in a best-effort manner.

        Missing or expired keys are skipped. This method does not raise
        for individual key failures.

        Args:
            keys (list[str]): List of cache keys to delete.
        """

        with self._lock:

            skipped_keys = []

            for key in keys:
                status = self._inspect_key(key=key)
                if status is KeyStatus.VALID:
                    self.cache.pop(key=key)
                    logger.debug(f"Key '{key}' deleted in bulk operation.")

                    # Eviction Policy Hook
                    self.eviction_policy.on_delete(self.cache, key)

                    # Record metrics
                    self.metrics.record_manual_deletion()
                    self.metrics.update_valid_keys_by_delta(-1)

                else:
                    skipped_keys.append(key)
                    self.metrics.record_miss()

            # Record metrics: update the total count
            self.metrics.update_total_keys(self.size())

            if skipped_keys:
                logger.warning(
                    f"The following keys were missing or expired and were skipped: {skipped_keys}"
                )

    def size(self) -> int:
        """
        Return the total number of entries in the cache,
        including expired entries.

        Returns:
            int: Total cache size.
        """

        with self._lock:
            return len(self.cache)

    def valid_size(self) -> int:
        """
        Return the number of valid (non-expired) entries in the cache.

        Performs a cleanup pass before calculating the size.

        Returns:
            int: Number of valid cache entries.
        """

        with self._lock:
            self.cleanup()
            return len(self.cache)

    def clear(self) -> None:
        """
        Remove all entries from the cache.

        Metrics are updated to reflect the cleared state, but
        the metrics system itself is not reset.
        """

        with self._lock:
            cleared_count = len(self.cache)
            self.cache.clear()

            # Reset the dynamic metric counters
            self.metrics.update_total_keys(0)
            self.metrics.update_valid_keys(0)
            self.metrics.record_manual_deletions(count=cleared_count)

            logger.info(f"Cache cleared. Removed {cleared_count} items.")

    def cleanup(self) -> None:
        """
        Remove all expired entries from the cache and
        synchronize cache metrics.
        """

        removed_count = 0

        with self._lock:

            # Perform the sweep
            for key in list(self.cache.keys()):
                # This helper handles the deletion and the 'expired_removal' count
                status = self._inspect_key(key=key)
                if status is KeyStatus.EXPIRED:
                    removed_count = removed_count + 1

            final_count = self.size()

            # SYNC THE METRICS
            # After a full sweep, physical length and valid size are identical.
            self.metrics.update_total_keys(final_count)  # Total Length
            self.metrics.update_valid_keys(final_count)  # Valid Size

            # logger.debug(f"Cleanup finished. Removed {removed_count} expired items.")

    def stop(self) -> None:
        """
        Gracefully stop the background cleanup thread.

        This method is automatically registered via `atexit`
        and is safe to call multiple times.
        """

        if not self._stop_event.is_set():
            logger.info("Stopping InMemoryCache...")
            self._stop_event.set()

            # Wait up to 2 seconds for the thread to wrap up
            self.cleanup_thread.join(timeout=2.0)

            if self.cleanup_thread.is_alive():
                logger.warning(
                    "Cleanup thread did not exit within timeout and will be terminated by the OS."
                )
            else:
                logger.info("InMemoryCache stopped gracefully.")

    def save_to_disk(self, filepath: str = None, use_timestamp: bool = False) -> None:
        """
        Persist the cache contents to disk.

        Args:
            filepath (Optional[str]): Custom file path.
            use_timestamp (bool): Whether to append a timestamp to the filename.

        Raises:
            CacheSaveError: If saving to disk fails.
        """

        timestamp = (
            use_timestamp if use_timestamp is not None else self.config.cache_timestamps
        )

        with self._lock:
            if not self.serializer.is_binary:
                data_to_serialize = {k: v.to_dict() for k, v in self.cache.items()}
            else:
                data_to_serialize = self.cache

        try:
            file_path = self.cache_file_manager.resolve_path(
                user_input=filepath,
                extension=self.serializer.extension,
                use_timestamp=timestamp,
            )
            serialized_data = self.serializer.serialize(data_to_serialize)
            self.cache_file_manager.write(path=file_path, data=serialized_data)

        except Exception as e:
            raise CacheSaveError(
                file_path if "file_path" in locals() else filepath, e
            ) from e

    def load_from_disk(self, filepath: str = None) -> None:
        """
        Load cache contents from disk.

        Existing cache contents are replaced.

        Args:
            filepath (Optional[str]): Path to the cache file.

        Raises:
            CacheLoadError: If loading fails or data is corrupted.
        """

        # Clear metrics and cache before loading new data

        with self._lock:
            self.cache.clear()
            self.metrics.reset()

        try:

            file_path = self.cache_file_manager.resolve_path(
                user_input=filepath,
                extension=self.serializer.extension,
                use_timestamp=False,
            )
            serialized_data = self.cache_file_manager.read(
                path=file_path, binary=self.serializer.is_binary
            )

            loaded_data = self.serializer.deserialize(serialized_data)

            with self._lock:
                if not self.serializer.is_binary:
                    # We have to do this, because non binary serializers cannot serialize datetime properly and they are being handled from_dict() func
                    new_cache = OrderedDict()
                    for k, v in loaded_data.items():
                        entry = CacheEntry.from_dict(v)
                        if entry is not None:
                            new_cache[k] = entry
                    self.cache = new_cache
                else:
                    self.cache = loaded_data

                # Sync physical metrics only
                total = len(self.cache)
                self.metrics.reset()
                self.metrics.update_total_keys(total)
                self.metrics.update_valid_keys(total)

        except Exception as e:
            raise CacheLoadError(filepath, e) from e

    def get_metrics_snapshot(self) -> dict:
        """
        Return a snapshot of the current cache metrics.

        The returned dictionary represents a read-only view
        of metrics at the time of the call.

        Returns:
            dict: Metrics snapshot.
        """

        with self._lock:
            return self.metrics.snapshot()

    def reset_metrics(self) -> None:
        """
        Reset all cache metrics to their initial state.

        Cache contents are not affected.
        """

        with self._lock:
            self.metrics.reset()

    def save_metrics_to_disk(
        self, filepath: str = None, use_timestamp: bool = False
    ) -> None:
        """
        Persist the current metrics snapshot to disk.

        Args:
            filepath (Optional[str]): Custom file path.
            use_timestamp (bool): Whether to append a timestamp to the filename.

        Raises:
            CacheMetricsSaveError: If saving metrics fails.
        """

        timestamp = (
            use_timestamp
            if use_timestamp is not None
            else self.config.cache_metrics_timestamps
        )

        try:
            with self._lock:
                metrics_data = self.metrics.snapshot()

            file_path = self.cache_metrics_file_manager.resolve_path(
                user_input=filepath,
                extension=self.metrics_serializer.extension,
                use_timestamp=timestamp,
            )

            serialized_data = self.metrics_serializer.serialize(metrics_data)
            self.cache_metrics_file_manager.write(path=file_path, data=serialized_data)

        except Exception as e:
            raise CacheMetricsSaveError(filepath or "unknown", e) from e

    def _is_ttl_valid(self, ttl: int) -> bool:
        """
        INTERNAL.

        Validate a TTL value.

        Purpose:
            Ensures that a TTL is a positive integer before it is used
            to compute expiration timestamps.

        Behavior:
            - Returns False for None, zero, negative, or non-integer values
            - Does not raise; validation errors are handled by the caller

        Returns:
            bool: True if TTL is valid, False otherwise.
        """

        if not ttl:
            return False

        try:
            ttl = int(ttl)
        except ValueError:
            return False

        if ttl <= 0:
            return False

        return True

    def _inspect_key(self, key: str) -> KeyStatus:
        """
        INTERNAL.

        Inspect the current state of a cache key without raising exceptions.

        Purpose:
            Centralized helper used by public APIs to determine whether a key
            is missing, expired, or valid.

        Behavior:
            - Removes expired entries from the cache
            - Triggers eviction-policy delete hooks for expired keys
            - Updates metrics for expired removals and key counts
            - Never raises exceptions

        Important:
            - This method MUTATES cache state and metrics
            - Must NOT be called multiple times for the same key in a single flow
            (expired keys are removed on first inspection)

        Returns:
            KeyStatus: MISSING, EXPIRED, or VALID
        """

        entry = self.cache.get(key)

        if entry is None:
            return KeyStatus.MISSING

        if entry.is_expired():
            self.cache.pop(key)

            # Eviction Policy Hook
            self.eviction_policy.on_delete(self.cache, key)

            # SYNC THE METRICS
            # After a deletion, we need to update the 'expired_removals' count and the total keys
            # We will also update the valid keys metric since we dont know if the background cleanup had caught onto or not
            # If we don't decrement it there, your current_valid_keys will stay artificially high until the next full cleanup() runs

            self.metrics.record_expired_removal()
            self.metrics.update_total_keys(len(self.cache))
            self.metrics.update_valid_keys_by_delta(-1)

            return KeyStatus.EXPIRED

        return KeyStatus.VALID

    def _internal_set(self, key: str, value: Any, ttl: int) -> None:
        """
        INTERNAL.

        Core insertion/update logic shared by multiple public APIs.

        Purpose:
            Implements the low-level mechanics of setting a cache entry without
            performing public API validation or raising user-facing exceptions.

        Behavior:
            - Determines whether the key is new, expired (ghost), or valid
            - Enforces cache capacity constraints
            - Computes expiration timestamps
            - Invokes eviction policy hooks
            - Synchronizes all relevant metrics

        Important:
            - Assumes TTL has already been validated
            - Mutates cache, eviction policy state, and metrics
            - Should only be called from methods holding the cache lock

        Notes:
            This method exists to avoid duplicating complex logic across
            set(), add(), update(), and set_many().
        """

        status = self._inspect_key(key)

        is_new = status is KeyStatus.MISSING
        is_ghost = status is KeyStatus.EXPIRED

        # ENFORCE CAPACITY
        if (is_new or is_ghost) and self.size() >= self.max_cache_size:
            self._ensure_capacity()

        expiration = utcnow() + timedelta(seconds=ttl)
        self.cache[key] = CacheEntry(value=value, expiration_time=expiration, ttl=ttl)

        # HOOK FOR EVICTION POLICY
        if is_new or is_ghost:
            self.eviction_policy.on_add(self.cache, key)
        else:
            self.eviction_policy.on_update(self.cache, key)

        # RECORD METRICS
        self.metrics.record_set()

        if is_new:
            self.metrics.update_total_keys(len(self.cache))
            self.metrics.update_valid_keys_by_delta(1)
        elif is_ghost:
            # Since the ghost was removed by the helper, total_keys count
            # is already updated inside _inspect_key.
            # We just need to sync the new total and increment valid count.
            self.metrics.update_total_keys(len(self.cache))
            self.metrics.update_valid_keys_by_delta(1)
        else:
            # It was a valid update to an existing key - sizes don't change!
            pass

    def _ensure_capacity(self) -> None:
        """
        INTERNAL.

        Ensure the cache does not exceed the configured maximum capacity.

        Purpose:
            Called before inserting new entries when the cache is at or above
            its size limit.

        Behavior:
            - Performs a cleanup pass to remove expired entries
            - Repeatedly evicts entries using the configured eviction policy
            - Records eviction events and synchronizes metrics

        Important:
            - Eviction continues until the cache size is strictly below capacity
            - Assumes eviction policy always returns a valid key
            - Mutates cache and metrics in place

        Raises:
            Exception: Propagates any unexpected errors from eviction policy logic.
        """

        logger.warning(
            f"Cache capacity ({self.max_cache_size}) reached. Evicting items."
        )

        self.cleanup()

        eviction_happened = False

        while self.size() >= self.max_cache_size:
            evicted_key = self.eviction_policy.select_eviction_key(self.cache)
            self.cache.pop(evicted_key)
            # Eviction Policy Hook
            self.eviction_policy.on_delete(self.cache, evicted_key)
            # Record Metrics
            self.metrics.record_eviction()
            eviction_happened = True

        if eviction_happened:
            new_size = self.size()
            self.metrics.update_total_keys(new_size)
            self.metrics.update_valid_keys(new_size)

    def _background_cleanup(self) -> None:
        """
        INTERNAL.

        Debug-only helper for inspecting cache contents.

        Purpose:
            Prints the current in-memory cache state in a human-readable format.

        Behavior:
            - Forces a cleanup pass before printing
            - Acquires the cache lock
            - Writes directly to stdout

        Important:
            - Not part of the public API
            - Should not be used in production code
        """

        logger.info("Background cleanup thread started.")
        # Loop as long as the stop signal hasn't been set
        try:
            while not self._stop_event.is_set():
                # Wait for the interval, but wake up instantly if stop_event is set
                if self._stop_event.wait(timeout=self.config.cleanup_interval):
                    break  # Exit loop if wait returned True (event was set)

                logger.debug("Periodic cleanup sweep triggered.")
                self.cleanup()
        except Exception as e:
            logger.error(
                "Background cleanup thread encountered an unhandled error",
                exc_info=True,
            )
        finally:
            logger.info("Background cleanup thread has shut down.")

    def _debug_print(self) -> None:
        """
        INTERNAL.

        Debug-only helper for inspecting cache contents.

        Purpose:
            Prints the current in-memory cache state in a human-readable format.

        Behavior:
            - Forces a cleanup pass before printing
            - Acquires the cache lock
            - Writes directly to stdout

        Important:
            - Not part of the public API
            - Should not be used in production code
        """

        with self._lock:

            self.cleanup()

            print(f"\n\tIn Memory Cache\n")
            for key in list(self.cache.keys()):
                print(f"\t\t{key} : {self.cache[key].value} : {self.cache[key].ttl}\n")
            print(f"\tEND\n")
