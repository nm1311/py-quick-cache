Objectives:

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
[-] Implement pluggable serialization formats ( e.g., JSON, Pickle).
[-] Implement a system to track the metrics 
[-] Convert the calculated metrics to properties and add them in snapshot
[-] Create a defaults or config file for the cache
[-] Bulk operation functions, set() function for upsurt
[-] Make JSON Serializer 
[-] Save metrics to file functions
[-] Make asdict function for cache entry
[-] Review _internal_set() 
[-] Take care of zombie threads on application exit.
[] Add Logging

[] Write test cases 
[] Add Custom exceptions
[] How will the users extend the config file and change only the things they need to change and use the other defaults

