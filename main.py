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
    [] Make the cache persistent to survive application restarts.
    [-] Ensure thread safety for concurrent access.
    [] Enhance expiry strategies to allow more flexibility.
"""

import time
from datetime import datetime, timedelta 
from collections import OrderedDict
import threading

class InMemoryCache:

    # Class-level constants
    ERROR_TTL_INVALID = "TTL must be a positive natural number"
    ERROR_KEY_NOT_EXIST = "Key doesn't exist or is expired"
    ERROR_KEY_EXISTS = "A valid Key already exists"
    CLEANUP_INTERVAL_SEC = 2
    MAX_CACHE_SIZE = 3


    def __init__(self):
        self.cache = OrderedDict()    # {"key" : ("value", "expiration_time (now + timedelta(ttl_sec))", "TTL")}
        self._lock = threading.RLock()

        # Start background cleanup thread (deamon=True to make sure it exits with main program)
        self.cleanup_thread = threading.Thread(target=self._background_cleanup, daemon=True)
        self.cleanup_thread.start()


    def _is_expired(self, key):
        return key in self.cache and datetime.now() > self.cache[key][1]
    

    def _remove_expired_or_lru_entries(self):
        self.cleanup()

        while self.size() >= self.MAX_CACHE_SIZE:
            self.cache.popitem(last=False)

        return(True, "Cache cleanup done")


    def add(self, key, value, ttl_sec):
        with self._lock:
            try:
                ttl = int(ttl_sec)
            except ValueError: 
                return (False, self.ERROR_TTL_INVALID)
            
            if ttl <= 0:
                return(False, self.ERROR_TTL_INVALID)
            
            if (key in self.cache):
                # Key expiry check
                if (not self._is_expired(key)):
                    return (False, self.ERROR_KEY_EXISTS)

            
            if self.size() >= self.MAX_CACHE_SIZE:
                self._remove_expired_or_lru_entries()

            # Add a new cache entry as no valid key exists
            self.cache[key] = (value, datetime.now() + timedelta(seconds=ttl), ttl_sec)
            self.cache.move_to_end(key)
            return (True, "Key added")
    

    def update(self, key, value, ttl_sec):
        with self._lock:
            try:
                ttl = int(ttl_sec)
            except ValueError: 
                return (False, self.ERROR_TTL_INVALID)
            
            if ttl <= 0:
                return(False, self.ERROR_TTL_INVALID)

            if key not in self.cache:
                return(False, self.ERROR_KEY_NOT_EXIST)

            self.cache[key] = (value, datetime.now() + timedelta(seconds=ttl), ttl_sec)
            self.cache.move_to_end(key)
            return (True, "Key updated")


    def get(self, key):
        with self._lock:
            if key not in self.cache:
                return (False, self.ERROR_KEY_NOT_EXIST)

            if (self._is_expired(key)):
                self.cache.pop(key)
                return (False, self.ERROR_KEY_NOT_EXIST)
            self.cache.move_to_end(key)
            return (True, self.cache[key][0])
    

    def delete(self, key):
        with self._lock:
            if key not in self.cache or self._is_expired(key):
                return(False, self.ERROR_KEY_NOT_EXIST)
            
            self.cache.pop(key)
            return (True, "Key deleted")
    

    def print(self):
        with self._lock:
            print(f"\n\tIn Memory Cache\n")
            for key in list(self.cache.keys()):
                if self._is_expired(key):
                    self.cache.pop(key)
                    continue

                print(f"\t\t{key} : {self.cache[key][0]} : {self.cache[key][2]}\n")

            print(f"\tEND\n")


    def size(self):
        with self._lock:
            return len(self.cache)


    def cleanup(self):
        with self._lock:
            expired_keys = set()

            for key in self.cache:
                if self._is_expired(key):
                    expired_keys.add(key)

            for key in expired_keys:
                self.cache.pop(key)

            return (True, f"Cleaned up {len(expired_keys)} expired keys")
    
    
    def _background_cleanup(self):
        """Background task that runs periodically to remove expired items."""
        while True:
            time.sleep(self.CLEANUP_INTERVAL_SEC)
            self.cleanup()


    

if __name__ == "__main__":

    my_cache = InMemoryCache()
    status = my_cache.add("city1", "Delhi", 5)
    print(status)
    status = my_cache.add("city2", "Mumbai", 5)
    print(status)
    status = my_cache.add("city3", "Pune", 5)
    print(status)
    status = my_cache.add("city4", "Kolkata", 5)
    print(status)
    status = my_cache.size()
    print(f"Cache Size: {status}")
    my_cache.print()
    status = my_cache.get("city")
    print(status)
    status = my_cache.update("city", "Los Angeles", 10)
    print(status)
    my_cache.print()
    status = my_cache.delete("city")
    print(status)
    status = my_cache.size()
    print(f"Cache Size: {status}")
    my_cache.print()
    status = my_cache.get("city")
    print(status)
    status = my_cache.add("country", "USA", 3)
    print(status)
    my_cache.print()
    import time
    time.sleep(4)
    status = my_cache.cleanup()
    print(status)
    my_cache.print()
    status = my_cache.get("country")
    print(status)


