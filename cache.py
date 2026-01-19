import time
from typing import Any, Optional
from datetime import datetime, timedelta
from collections import OrderedDict
import threading
from dataclasses import dataclass

import registry.default_registries as default_registries
from config import CacheConfig
from registry.registry import create_eviction_policy, create_serializer
from backend import FileManager
from metrics import CacheMetrics, NoOpMetrics


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
    ERROR_TTL_INVALID_MSG = "TTL must be a positive natural number"
    ERROR_KEY_NOT_EXIST_MSG = "Key doesn't exist or is expired"
    ERROR_KEY_EXISTS_MSG = "A valid Key already exists"
    ERROR_FILE_SAVE_MSG = "An error occured while saving the file"
    ERROR_FILE_LOAD_MSG = "An error occured while loading the file"
    SUCCESS_FILE_SAVE_MSG = "File saved successfully"
    SUCCESS_FILE_LOAD_MSG = "File loaded successfully"
    SUCCESS_KEY_ADD_MSG = "Key added successfully"
    SUCCESS_KEY_SET_MSG = "Key set successfully"
    SUCCESS_KEY_SET_MANY_MSG = "Successfully synchronized multiple keys to cache."
    SUCCESS_KEY_UPDATE_MSG = "Key updated successfully"
    SUCCESS_KEY_DELETE_MSG = "Key deleted successfully"
    SUCCESS_KEY_DELETE_MANY_MSG = "Deleted multiple keys successfully"
    SUCCESS_EVICTION_MSG = "Cache capacity enforced. Items evicted to make room"
    CACHE_CLEAR_MSG = "Cache cleared successfully"

    def __init__(
        self,
        config: Optional[CacheConfig] = None,
    ) -> None:

        # Load default config if no config is provided
        self.config = config or CacheConfig()

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

    def _is_ttl_valid(self, ttl: int) -> bool:
        if not ttl:
            return False

        try:
            ttl = int(ttl)
        except ValueError:
            return False

        if ttl <= 0:
            return False

        return True

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

        eviction_happened = False

        while self.size() >= self.max_cache_size:
            evicted_key = self.eviction_policy.select_eviction_key(self.cache)
            self.cache.pop(evicted_key)
            self.metrics.record_eviction()
            eviction_happened = True

        if eviction_happened:
            new_size = self.size()
            self.metrics.update_total_keys(new_size)
            self.metrics.update_valid_keys(new_size)

        return (True, self.SUCCESS_EVICTION_MSG)

    def add(self, key: str, value: Any, ttl_sec: int = None) -> CacheResponse:
        with self._lock:

            if not ttl_sec:
                ttl = self.config.default_ttl
            else:
                if self._is_ttl_valid(ttl_sec):
                    ttl = int(ttl_sec)

            if key in self.cache:

                if self._check_key_validity_and_remove_expired(key) is True:
                    # If the key is VALID, we cannot add a duplicate.

                    # SYNC THE METRICS
                    # Record a failed set operation.
                    self.metrics.record_failed_op()

                    return CacheResponse(False, self.ERROR_KEY_EXISTS_MSG)

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

            return CacheResponse(True, self.SUCCESS_KEY_ADD_MSG)

    def update(self, key: str, value: Any, ttl_sec: int) -> CacheResponse:
        with self._lock:

            if self._is_ttl_valid(ttl_sec):
                ttl = int(ttl_sec)

            if key not in self.cache:
                self.metrics.record_failed_op()
                return CacheResponse(False, self.ERROR_KEY_NOT_EXIST_MSG)

            if self._check_key_validity_and_remove_expired(key) is False:
                self.metrics.record_failed_op()
                return CacheResponse(False, self.ERROR_KEY_NOT_EXIST_MSG)

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

            return CacheResponse(True, self.SUCCESS_KEY_UPDATE_MSG)

    def get(self, key: str) -> CacheResponse:
        self.metrics.record_get()

        with self._lock:

            if key not in self.cache:
                self.metrics.record_miss()
                return CacheResponse(False, self.ERROR_KEY_NOT_EXIST_MSG)

            if self._check_key_validity_and_remove_expired(key) is False:
                self.metrics.record_miss()
                return CacheResponse(False, self.ERROR_KEY_NOT_EXIST_MSG)

            # --- PLUGGABLE HOOK FOR EVICTION POLICY ---
            self.eviction_policy.on_access(self.cache, key)

            self.metrics.record_hit()
            return CacheResponse(True, self.cache[key].value)

    def delete(self, key: str) -> CacheResponse:
        with self._lock:
            if key not in self.cache:
                return CacheResponse(False, self.ERROR_KEY_NOT_EXIST_MSG)

            if self._check_key_validity_and_remove_expired(key) is False:
                return CacheResponse(False, self.ERROR_KEY_NOT_EXIST_MSG)

            self.cache.pop(key)

            # SYNC THE METRICS
            # Record manual deletion, and update the total and valid keys accordingly
            self.metrics.record_manual_deletion()
            self.metrics.update_total_keys(self.size())
            self.metrics.update_valid_keys_by_delta(delta=-1)

            return CacheResponse(True, self.SUCCESS_KEY_DELETE_MSG)

    def _internal_set(self, key, value, ttl):
        is_new = key not in self.cache
        is_ghost = (not is_new) and (
            not self._check_key_validity_and_remove_expired(key=key)
        )

        # ENFORCE CAPACITY
        if (is_new or is_ghost) and self.size() >= self.max_cache_size:
            self._ensure_capacity()

        expiration = datetime.now() + timedelta(seconds=ttl)
        self.cache[key] = CacheEntry(value=value, expiration_time=expiration, ttl=ttl)

        # HOOK FOR EVICTION POLICY
        self.eviction_policy.on_update(self.cache, key)

        # RECORD METRICS
        self.metrics.record_set()

        if is_new:
            self.metrics.update_total_keys(len(self.cache))
            self.metrics.update_valid_keys_by_delta(1)
        elif is_ghost:
            # Since the ghost was removed by the helper, total_keys count
            # is already updated inside _check_key_validity_and_remove_expired.
            # We just need to sync the new total and increment valid count.
            self.metrics.update_total_keys(len(self.cache))
            self.metrics.update_valid_keys_by_delta(1)
        else:
            # It was a valid update to an existing key - sizes don't change!
            pass

    def set(self, key: str, value: Any, ttl_sec: int = None) -> CacheResponse:
        """This function works as Upsert."""
        if self._is_ttl_valid(ttl=ttl_sec):
            ttl = int(ttl)
        else:
            ttl = self.config.default_ttl

        with self._lock:
            self._internal_set(key, value, ttl)
            return CacheResponse(success=True, message=self.SUCCESS_KEY_SET_MSG)

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
                print(e)
                return CacheResponse(success=False, message=self.ERROR_FILE_SAVE_MSG)

            return CacheResponse(success=True, message=self.SUCCESS_FILE_SAVE_MSG)

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

            loaded_data = self.serializer.deserialize(serialized_data)

            with self._lock:
                if not self.serializer.is_binary:
                    new_cache = OrderedDict()
                    for k, v in loaded_data.items():
                        entry = CacheEntry.from_dict(v)
                        if entry is not None:
                            new_cache[k] = entry
                    self.cache = new_cache
                else:
                    self.cache = loaded_data

                # Do a cleanup here, it will automatically remove the expired entries and set the metrics
                self.cleanup()

            return CacheResponse(success=True, message=self.SUCCESS_FILE_LOAD_MSG)

        except Exception as e:
            print(e)
            return CacheResponse(
                success=False,
                message=f"{self.ERROR_FILE_LOAD_MSG} : {str(e)}",
            )

    def _background_cleanup(self) -> None:
        """Background task that runs periodically to remove expired items."""
        # Loop as long as the stop signal hasn't been set
        while not self._stop_event.is_set():
            # Wait for the interval, but wake up instantly if stop_event is set
            if self._stop_event.wait(timeout=self.config.cleanup_interval):
                break  # Exit loop if wait returned True (event was set)

            self.cleanup()

    def get_metrics_snapshot(self):
        with self._lock:
            return self.metrics.snapshot()

    def clear(self) -> CacheResponse:
        """Wipes all data and resets metrics."""
        with self._lock:
            self.cache.clear()
            # Reset the dynamic metric counters
            self.metrics.update_total_keys(0)
            self.metrics.update_valid_keys(0)
            return CacheResponse(success=True, message=self.CACHE_CLEAR_MSG)

    def set_many(self, data: dict[str, Any], ttl_sec: int = None) -> CacheResponse:
        """Bulk operation using 'Set' (Upsert) logic."""
        if self._is_ttl_valid(ttl=ttl_sec):
            ttl = int(ttl_sec)
        else:
            ttl = self.config.default_ttl

        with self._lock:
            for key, value in data.items():
                # We use the internal method that doesn't care about ghosts or existing keys
                self._internal_set(key, value, ttl)

        return CacheResponse(
            success=True,
            message=f"{self.SUCCESS_KEY_SET_MANY_MSG} : TOTAL SET: {len(data)}",
        )

    def get_many(self, keys: list[str]) -> dict[str, Any]:
        results = {}

        with self._lock:
            # Record the overall bulk operation
            self.metrics.record_get()

            for key in keys:
                # Case A: Missing Key
                if key not in self.cache:
                    self.metrics.record_miss()
                    continue

                # Case B: Ghost Key (Expired)
                if not self._check_key_validity_and_remove_expired(key):
                    # no need to record metrics here, the funciton is alrady doing that
                    continue
                else:
                    # Case C: Valid Hit
                    self.metrics.record_hit()

                # EVICTION POLICY HOOK
                self.eviction_policy.on_access(self.cache, key)

                results[key] = self.cache[key].value

        return results

    def delete_many(self, keys: list[str]) -> CacheResponse:
        """
        Deletes multiple keys.
        Does not error if keys are missing; ensures they are removed.
        """

        deleted_count = 0

        with self._lock:
            for key in keys:
                if self._check_key_validity_and_remove_expired(key=key) is True:
                    self.cache.pop(key=key)
                    deleted_count = deleted_count + 1

                    # Record metrics
                    self.metrics.record_manual_deletion()
                    self.metrics.update_valid_keys_by_delta(-1)

                else:
                    continue

            # Record metrics: update the total count
            self.metrics.update_total_keys(self.size())

            return CacheResponse(
                success=True,
                message=f"{self.SUCCESS_KEY_DELETE_MANY_MSG}. Attempted deletion of {len(keys)} keys. {deleted_count} were actually removed.",
            )

    def save_metrics_to_disk(
        self, filepath: str = None, use_timestamp: bool = False
    ) -> CacheResponse:

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
            return CacheResponse(success=True, message=self.SUCCESS_FILE_SAVE_MSG)

        except Exception as e:
            print(e)
            return CacheResponse(
                success=False, message=f"{self.ERROR_FILE_SAVE_MSG} : {str(e)}"
            )

    def stop(self):
        """Gracefully stops the background cleanup thread."""
        self._stop_event.set()  # Trigger the stop signal
        self.cleanup_thread.join(timeout=2.0)  # Wait for it to finish
