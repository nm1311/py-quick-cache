import time
from typing import Any, Optional
from datetime import datetime, timedelta
from collections import OrderedDict
import threading
from dataclasses import dataclass

import default_registries
from config import CacheConfig
from registry import create_eviction_policy, create_serializer
from backend import FileManager
from metrics import CacheMetrics, NoOpMetrics


@dataclass(slots=True)
class CacheEntry:
    value: Any
    expiration_time: datetime
    ttl: int

    def is_expired(self) -> bool:
        """Returns true if expired"""
        return datetime.now() > self.expiration_time


@dataclass(slots=True)
class CacheResponse:
    success: bool
    message: str
    data: Optional[Any] = None


class InMemoryCache:
    """
    In-Memory Cache.
    """

    # Class-level constants
    ERROR_TTL_INVALID = "TTL must be a positive natural number"
    ERROR_KEY_NOT_EXIST = "Key doesn't exist or is expired"
    ERROR_KEY_EXISTS = "A valid Key already exists"
    ERROR_FILE_SAVE = "An error occured while saving the file"
    ERROR_FILE_LOAD = "An error occured while loading the file"
    SUCCESS_FILE_SAVE = "File saved successfully"
    SUCCESS_FILE_LOAD = "File loaded successfully"
    SUCCESS_KEY_ADD = "Key added successfully"
    SUCCESS_KEY_UPDATE = "Key updated successfully"
    SUCCESS_KEY_DELETE = "Key deleted successfully"
    SUCCESS_EVICTION = "Cache capacity enforced. Items evicted to make room."

    def __init__(
        self,
        config: Optional[CacheConfig] = None,
    ) -> None:

        # Load default config if no config is provided
        self.config = config or CacheConfig()

        self.eviction_policy = create_eviction_policy(self.config.eviction_policy)
        self.serializer = create_serializer(self.config.serializer)

        self.metrics = CacheMetrics() if self.config.enable_metrics else NoOpMetrics()

        self.cache_file_manager = FileManager(
            default_dir=self.config.storage_dir,
            default_filename=self.config.filename,
        )

        # In memory Cache
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.max_cache_size = self.config.max_size

        # Start background cleanup thread (deamon=True to make sure it exits with main program)
        self._lock: threading.RLock = threading.RLock()
        # self._stop_event = threading.Event() # The "Stop Signal" in case our main program wants to exit
        self.cleanup_thread = threading.Thread(
            target=self._background_cleanup, daemon=True
        )
        self.cleanup_thread.start()

    def _check_key_validity_and_remove_expired(self, key: str) -> bool:
        """
        Checks if a key is valid. If it's expired, it removes it.
        Returns True if the key is valid and still in cache.
        Returns False if the key was missing or pruned.
        """
        entry = self.cache.get(key)

        if entry is None:
            return False

        if entry.is_expired():
            self.cache.pop(key)

            # SYNC THE METRICS
            # After a deletion, we need to update the 'expired_removals' count and the total keys
            # We will also update the valid keys metric since we dont know if the background cleanup had caught onto or not
            # If we don't decrement it there, your current_valid_keys will stay artificially high until the next full cleanup() runs
            self.metrics.record_expired_removal()
            self.metrics.update_total_keys(len(self.cache))
            self.metrics.update_valid_keys_by_delta(
                delta=-1
            )  # decrease valid keys by 1

            return False

        return True

    def cleanup(self) -> dict:
        """
        1. Removes all expired items.
        2. Syncs physical and logical metrics.
        3. Returns a summary of what was done.
        """
        with self._lock:
            initial_physical = self.size()

            # Perform the sweep
            for key in list(self.cache.keys()):
                # This helper handles the deletion and the 'expired_removal' count
                self._check_key_validity_and_remove_expired(key)

            final_count = self.size()
            removed_count = initial_physical - final_count

            # SYNC THE METRICS
            # After a full sweep, physical length and valid size are identical.
            self.metrics.update_total_keys(final_count)  # Total Length
            self.metrics.update_valid_keys(final_count)  # Valid Size

            return {
                "success": True,
                "items_removed": removed_count,
                "current_size": final_count,
            }

    def _ensure_capacity(self) -> tuple[bool, str]:
        self.cleanup()

        while self.size() >= self.max_cache_size:
            evicted_key = self.eviction_policy.select_eviction_key(self.cache)
            self.cache.pop(evicted_key)

            # SYNC THE METRICS
            # We will record the eviction and update the total keys and valid keys both since all the keys are valid at this point
            self.metrics.record_eviction()
            self.metrics.update_total_keys(self.size())
            self.metrics.update_valid_keys(self.size())

        return (True, self.SUCCESS_EVICTION)

    def add(self, key: str, value: Any, ttl_sec: int = None) -> CacheResponse:
        with self._lock:

            if not ttl_sec:
                ttl = self.config.default_ttl
            else:
                try:
                    ttl = int(ttl_sec)
                except ValueError:
                    return CacheResponse(False, self.ERROR_TTL_INVALID)

                if ttl <= 0:
                    return CacheResponse(False, self.ERROR_TTL_INVALID)

            if key in self.cache:

                if self._check_key_validity_and_remove_expired(key) is True:
                    # If the key is VALID, we cannot add a duplicate.

                    # SYNC THE METRICS
                    # Record a failed set operation.
                    self.metrics.record_failed_op()

                    return CacheResponse(False, self.ERROR_KEY_EXISTS)

            if self.size() >= self.max_cache_size:
                self._ensure_capacity()

            # Add a new cache entry as no valid key exists
            self.cache[key] = CacheEntry(
                value=value,
                expiration_time=datetime.now() + timedelta(seconds=ttl),
                ttl=ttl_sec,
            )

            # SYNC THE METRICS
            # Record a successful set operation and update the total keys as well as valid keys since we know one more valid key is added
            self.metrics.record_set()
            self.metrics.update_total_keys(self.size())
            self.metrics.update_valid_keys_by_delta(delta=1)

            # --- PLUGGABLE HOOK FOR EVICTION POLICY ---
            self.eviction_policy.on_update(self.cache, key)

            return CacheResponse(True, self.SUCCESS_KEY_ADD)

    def update(self, key: str, value: Any, ttl_sec: int) -> CacheResponse:
        with self._lock:
            try:
                ttl = int(ttl_sec)
            except ValueError:
                return CacheResponse(False, self.ERROR_TTL_INVALID)

            if ttl <= 0:
                return CacheResponse(False, self.ERROR_TTL_INVALID)

            if key not in self.cache:
                self.metrics.record_failed_op()
                return CacheResponse(False, self.ERROR_KEY_NOT_EXIST)

            if self._check_key_validity_and_remove_expired(key) is False:
                self.metrics.record_failed_op()
                return CacheResponse(False, self.ERROR_KEY_NOT_EXIST)

            self.cache[key] = CacheEntry(
                value=value,
                expiration_time=datetime.now() + timedelta(seconds=ttl),
                ttl=ttl_sec,
            )

            # --- PLUGGABLE HOOK FOR EVICTION POLICY ---
            self.eviction_policy.on_update(self.cache, key)

            # SYNC THE METRICS
            # Record a successful set and update the total and valid keys
            self.metrics.record_set()
            self.metrics.update_total_keys(self.size())
            self.metrics.update_valid_keys_by_delta(delta=0)

            return CacheResponse(True, self.SUCCESS_KEY_UPDATE)

    def get(self, key: str) -> CacheResponse:
        self.metrics.record_get()

        with self._lock:

            if key not in self.cache:
                self.metrics.record_miss()
                return CacheResponse(False, self.ERROR_KEY_NOT_EXIST)

            if self._check_key_validity_and_remove_expired(key) is False:
                self.metrics.record_miss()
                return CacheResponse(False, self.ERROR_KEY_NOT_EXIST)

            # --- PLUGGABLE HOOK FOR EVICTION POLICY ---
            self.eviction_policy.on_access(self.cache, key)

            self.metrics.record_hit()
            return CacheResponse(True, self.cache[key].value)

    def delete(self, key: str) -> CacheResponse:
        with self._lock:
            if key not in self.cache:
                return CacheResponse(False, self.ERROR_KEY_NOT_EXIST)

            if self._check_key_validity_and_remove_expired(key) is False:
                return CacheResponse(False, self.ERROR_KEY_NOT_EXIST)

            self.cache.pop(key)

            # SYNC THE METRICS
            # Record manual deletion, and update the total and valid keys accordingly
            self.metrics.record_manual_deletion()
            self.metrics.update_total_keys(self.size())
            self.metrics.update_valid_keys_by_delta(delta=-1)

            return CacheResponse(True, self.SUCCESS_KEY_DELETE)

    def print(self):
        with self._lock:

            self.cleanup()

            print(f"\n\tIn Memory Cache\n")
            for key in list(self.cache.keys()):
                print(f"\t\t{key} : {self.cache[key].value} : {self.cache[key].ttl}\n")
            print(f"\tEND\n")

    def size(self) -> int:
        with self._lock:
            return len(self.cache)

    def valid_size(self) -> int:
        with self._lock:
            self.cleanup()
            return len(self.cache)

    def save_to_disk(
        self, filepath: str = None, use_timestamp: bool = False
    ) -> CacheResponse:

        try:
            file_path = self.cache_file_manager.resolve_path(
                user_input=filepath,
                extension=self.serializer.extension,
                use_timestamp=use_timestamp,
            )
            serialized_data = self.serializer.serialize(self.cache)
            self.cache_file_manager.write(path=file_path, data=serialized_data)
        except Exception as e:
            print(e)
            return CacheResponse(success=False, message=self.ERROR_FILE_SAVE)

        return CacheResponse(success=True, message=self.SUCCESS_FILE_SAVE)

    def load_from_disk(self, filepath: str = None):
        try:
            file_path = self.cache_file_manager.resolve_path(
                user_input=filepath,
                extension=self.serializer.extension,
                use_timestamp=False,
            )
            serialized_data = self.cache_file_manager.read(
                path=file_path, binary=self.serializer.is_binary
            )
            loaded_cache = self.serializer.deserialize(serialized_data)

            with self._lock:
                self.cache = loaded_cache

        except Exception as e:
            print(e)
            return CacheResponse(
                success=False,
                message=f"{self.ERROR_FILE_LOAD} : {str(e)}",
            )

        return CacheResponse(success=True, message=self.SUCCESS_FILE_LOAD)

    def _background_cleanup(self) -> None:
        """Background task that runs periodically to remove expired items."""
        while True:
            time.sleep(self.config.cleanup_interval)
            self.cleanup()

    def get_metrics_snapshot(self):
        with self._lock:
            return self.metrics.snapshot()
