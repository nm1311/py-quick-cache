from typing import Any, Optional
from datetime import datetime, timedelta, timezone
from collections import OrderedDict
import threading
from enum import Enum, auto
from dataclasses import dataclass
import atexit

from .base_cache import BaseCache
from .registry.registry import create_eviction_policy, create_serializer
from .registry import default_registries
from .config import QuickCacheConfig
from .backend import FileManager
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
from .helpers import utcnow

import logging

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


@dataclass(slots=True)
class CacheEntry:
    value: Any
    expiration_time: datetime
    ttl: int

    def to_dict(self) -> dict:
        """Converts the entry into a JSON-serializable dictionary."""
        return {
            "value": self.value,
            "expiration_time": self.expiration_time.isoformat(),  # Handle datetime conversion here
            "ttl": self.ttl,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CacheEntry":
        """Reconstructs a CacheEntry from a dictionary."""
        return cls(
            value=data["value"],
            expiration_time=datetime.fromisoformat(
                data["expiration_time"]
            ),  # Revert string to datetime
            ttl=data["ttl"],
        )

    def is_expired(self) -> bool:
        """Returns true if expired"""
        return utcnow() > self.expiration_time


class KeyStatus(Enum):
    MISSING = auto()
    EXPIRED = auto()
    VALID = auto()


class QuickCache(BaseCache):
    """
    In-Memory Cache.
    """

    def __init__(
        self,
        config: Optional[QuickCacheConfig] = None,
    ) -> None:

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
        """Returns the value of a valid key in cache else raise exceptions"""

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
        """Upsert a key, if no ttl provides, uses the default value"""

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
        """Insert the key only if no valid key exists"""

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
        """Updates the value of an existing valid key. Raises if key doesn't exist or is expired."""

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
        """Deletes a key from the cache. Raises if key doesn't exist or is expired"""

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
        Bulk upsert multiple keys.
        Each key is treated as an individual set operation for metrics.
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
        Expired or missing keys are skipped.
        Returns a dictionary of only valid keys to their values.
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
        Deletes multiple keys from the cache in a best-effort way.
        Missing or expired keys are skipped. Returns None.
        Logs a warning if any keys were missing or expired.
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
        """Returns the total size of the cache that includes the expired keys as well"""

        with self._lock:
            return len(self.cache)

    def valid_size(self) -> int:
        """Returns the total valid keys in the cache, also does a cleanup before calculating"""

        with self._lock:
            self.cleanup()
            return len(self.cache)

    def clear(self) -> None:
        """Wipes all data from the cache, do not reset metrics and returns None on success"""

        with self._lock:
            cleared_count = len(self.cache)
            self.cache.clear()

            # Reset the dynamic metric counters
            self.metrics.update_total_keys(0)
            self.metrics.update_valid_keys(0)
            self.metrics.record_manual_deletions(count=cleared_count)

            logger.info(f"Cache cleared. Removed {cleared_count} items.")

    def cleanup(self) -> None:
        """Removes expired items and synchronizes metrics"""
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
        """Gracefully stops the background cleanup thread."""
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
        Saves cache data to disk.
        Raises CacheSaveError on failure.
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
        Loads cache data from disk.
        Raises an exception if loading fails.
        Returns None on success.
        """

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
        Returns a snapshot of the current cache metrics.
        The returned dictionary is a read-only snapshot representing the
        cache state at the time of the call.
        """
        with self._lock:
            return self.metrics.snapshot()

    def reset_metrics(self) -> None:
        """
        Resets all cache metrics to their initial state.
        This clears counters such as hits, misses, evictions, and key counts.
        Does not affect cache contents.
        """

        with self._lock:
            self.metrics.reset()

    def save_metrics_to_disk(
        self, filepath: str = None, use_timestamp: bool = False
    ) -> None:
        """
        Saves the current cache metrics snapshot to disk.
        Raises on failure.
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
        """Returns True if ttl is present, and is an integer"""
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
        Inspects key state.
        Handles expiration removal + metrics.
        Does NOT raise.
        it mutates metrics and must never be called twice for same expired key
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
        Insert or update a cache entry without performing validation or public API checks.

        This method handles the core logic for setting a key in the cache:
        - Determines whether the key is new, expired (ghost), or already valid
        - Enforces cache capacity constraints when inserting new or expired keys
        - Computes and assigns the expiration time based on the provided TTL
        - Updates the eviction policy
        - Records and synchronizes cache metrics

        This method is intended for internal use only and assumes that all
        required validation (such as key/value checks) has already been performed
        by the caller.
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
        Ensure the cache size does not exceed the configured maximum capacity.
        This method is invoked when inserting a new entry would cause the cache
        to exceed `max_cache_size`. It performs the following steps:
        - Triggers a cleanup pass to remove expired entries
        - Repeatedly evicts entries using the configured eviction policy until
        the cache size is within capacity
        - Records eviction events and synchronizes cache metrics
        - Eviction is guaranteed to complete unless the eviction policy fails,
        in which case an exception is propagated.
        - This method mutates the cache and metrics in place and is intended
        for internal use only.
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
        """Background task that runs periodically to remove expired items."""
        # Loop as long as the stop signal hasn't been set

        logger.info("Background cleanup thread started.")
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
        with self._lock:

            self.cleanup()

            print(f"\n\tIn Memory Cache\n")
            for key in list(self.cache.keys()):
                print(f"\t\t{key} : {self.cache[key].value} : {self.cache[key].ttl}\n")
            print(f"\tEND\n")
