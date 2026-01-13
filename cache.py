"""Objectives: 
    [-] Store key-value pairs in a dictionary
    [-] Implement TTL (Time To Live) functionality for cache entries
    [-] Remove expired entries automatically
    [-] Provide methods to get, set, and delete cache entries
    [-] Implement a method to print the current state of the cache
    [-] Convert the code into a class-based structure for better organization
    [-] Implement a method to get the current size of the cache
    [-] Implement a method to cleanup the expired entries in the cache
    [-] Background cleanup to handle expired items automatically.
    [-] Implement LRU (Least Recently Used) eviction for cache size management.
    [-] Implement pluggable eviction policies (Strategy Pattern).
    [-] Ensure thread safety for concurrent access.
    [-] Enhance expiry strategies to allow more flexibility.
    [-] Make the cache entry and cache response more clear, e.g., using a dataclass or namedtuple.
    [-] Make the cache persistent to survive application restarts.
    [-] Implement pluggable serialization formats (e.g., JSON, Pickle).
    [] Take care of zombie threads on application exit.
"""

import time
from typing import Any, Optional
from datetime import datetime, timedelta 
from collections import OrderedDict
import threading
from dataclasses import dataclass

from eviction_policy import EvictionPolicy, LRUEvictionPolicy
from serializer import BaseSerializer, PickleSerializer
from storage import FileManager


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
    
    DEFAULT_CACHE_DIR = "cache_storage"
    DEFAULT_CACHE_FILENAME = "cache"
    
    DEFAULT_TTL_SEC = 5
    CLEANUP_INTERVAL_SEC = 2
    DEFAULT_MAX_CACHE_SIZE = 3


    def __init__(self, max_cache_size: int = None, eviction_policy: EvictionPolicy = None, serializer: BaseSerializer = None) -> None:
    
        self.eviction_policy = eviction_policy or LRUEvictionPolicy() #Default
        self.serializer = serializer or PickleSerializer() #Default
        self.cache_file_manager = FileManager(default_dir=self.DEFAULT_CACHE_DIR, default_filename=self.DEFAULT_CACHE_FILENAME)

        # In memory Cache
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.max_cache_size = max_cache_size or self.DEFAULT_MAX_CACHE_SIZE
        
        # Start background cleanup thread (deamon=True to make sure it exits with main program)
        self._lock: threading.RLock = threading.RLock()
        #self._stop_event = threading.Event() # The "Stop Signal" in case our main program wants to exit
        self.cleanup_thread = threading.Thread(target=self._background_cleanup, daemon=True)
        self.cleanup_thread.start()


    def _is_expired(self, key: str) -> bool:
        return key in self.cache and self.cache[key].is_expired()
    

    def cleanup(self) -> tuple[bool, int, str]:
        with self._lock:
            expired_keys = set()

            for key in self.cache:
                if self.cache[key].is_expired():
                    expired_keys.add(key)

            for key in expired_keys:
                self.cache.pop(key)

            return (True, len(expired_keys), "Cleanup completed")
    

    def _ensure_capacity(self) -> tuple[bool, str]:
        self.cleanup()

        while self.size() >= self.max_cache_size:
            evicted_key = self.eviction_policy.select_eviction_key(self.cache)
            self.cache.pop(evicted_key)

        return(True, "Cache capacity enforced. Items evicted to make room.")


    def add(self, key: str, value: Any, ttl_sec: int = None) -> CacheResponse:
        with self._lock:

            if not ttl_sec:
                ttl = self.DEFAULT_TTL_SEC
            else:
                try:
                    ttl = int(ttl_sec)
                except ValueError:
                    return CacheResponse(False, self.ERROR_TTL_INVALID)
            
                if ttl <= 0:
                    return CacheResponse(False, self.ERROR_TTL_INVALID)
            
            if (key in self.cache):
                # Key expiry check
                if (not self.cache[key].is_expired()):
                    return CacheResponse(False, self.ERROR_KEY_EXISTS)

            
            if self.size() >= self.max_cache_size:
                self._ensure_capacity()

            # Add a new cache entry as no valid key exists
            self.cache[key] = CacheEntry(
                value=value,
                expiration_time=datetime.now() + timedelta(seconds=ttl),
                ttl=ttl_sec
            )

            # --- PLUGGABLE HOOK FOR EVICTION POLICY ---
            self.eviction_policy.on_update(self.cache, key)

            return CacheResponse(True, "Key added")
    

    def update(self, key: str, value: Any, ttl_sec: int) -> CacheResponse:
        with self._lock:
            try:
                ttl = int(ttl_sec)
            except ValueError: 
                return CacheResponse(False, self.ERROR_TTL_INVALID)
            
            if ttl <= 0:
                return CacheResponse(False, self.ERROR_TTL_INVALID)

            if key not in self.cache:
                return CacheResponse(False, self.ERROR_KEY_NOT_EXIST)

            self.cache[key] = CacheEntry(
                value=value,
                expiration_time=datetime.now() + timedelta(seconds=ttl),
                ttl=ttl_sec
            )
            
            # --- PLUGGABLE HOOK FOR EVICTION POLICY ---
            self.eviction_policy.on_update(self.cache, key)

            return CacheResponse(True, "Key updated")


    def get(self, key: str) -> CacheResponse:
        with self._lock:
            if key not in self.cache:
                return CacheResponse(False, self.ERROR_KEY_NOT_EXIST)

            if (self.cache[key].is_expired()):
                self.cache.pop(key)
                return CacheResponse(False, self.ERROR_KEY_NOT_EXIST)
            
            # --- PLUGGABLE HOOK FOR EVICTION POLICY ---
            self.eviction_policy.on_access(self.cache, key)

            return CacheResponse(True, self.cache[key].value)


    def delete(self, key: str) -> CacheResponse:
        with self._lock:
            if key not in self.cache:
                return CacheResponse(False, self.ERROR_KEY_NOT_EXIST)
            
            if self.cache[key].is_expired():
                self.cache.pop(key)
                return CacheResponse(False, self.ERROR_KEY_NOT_EXIST)
            
            self.cache.pop(key)
            return CacheResponse(True, "Key deleted")

    
    def print(self):
        with self._lock:
            print(f"\n\tIn Memory Cache\n")
            for key in list(self.cache.keys()):
                if self.cache[key].is_expired():
                    self.cache.pop(key)
                    continue

                print(f"\t\t{key} : {self.cache[key].value} : {self.cache[key].ttl}\n")
            print(f"\tEND\n")


    def size(self)-> int:
        with self._lock:
            return len(self.cache)


    def save_to_disk(self, filepath: str = None, use_timestamp: bool = False) -> CacheResponse:
        
        try:
            file_path = self.cache_file_manager.resolve_path(user_input=filepath, extension=self.serializer.extension, use_timestamp=use_timestamp)
            serialized_data = self.serializer.serialize(self.cache)
            self.cache_file_manager.write(path=file_path, data=serialized_data)
        except Exception as e:
            print(e)
            return CacheResponse(success=False, message=self.ERROR_FILE_SAVE)
        
        return CacheResponse(success=True, message=self.SUCCESS_FILE_SAVE)


    def load_from_disk(self, filepath: str = None):
        try:
            file_path = self.cache_file_manager.resolve_path(user_input=filepath, extension=self.serializer.extension, use_timestamp=False)
            serialized_data = self.cache_file_manager.read(path=file_path, binary=self.serializer.is_binary)
            loaded_cache = self.serializer.deserialize(serialized_data)

            with self._lock:
                self.cache = loaded_cache

        except Exception as e:
            print(e)
            return CacheResponse(success=False, message=f"An error occured while loading the file : {str(e)}")
        
        return CacheResponse(success=True, message="File loaded successfully")


    def _background_cleanup(self)-> None:
        """Background task that runs periodically to remove expired items."""
        while True:
            time.sleep(self.CLEANUP_INTERVAL_SEC)
            self.cleanup()
