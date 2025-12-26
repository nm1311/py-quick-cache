"""Objectives: 
    [] Store key-value pairs in a dictionary
    [] Implement TTL (Time To Live) functionality for cache entries
    [] Remove expired entries automatically
    [] Provide methods to get, set, and delete cache entries
"""


from datetime import datetime, timedelta 

cache = {
    # "key" : ("value", "expiration_time (now + timedelta(ttl_sec))", "TTL"), 
}

def is_expired(key):
    global cache
    return datetime.now() > cache[key][1]
    

def add_cache_item(key, value, ttl_sec):
    global cache

    try:
        ttl = int(ttl_sec)
    except ValueError: 
        return (False, "TTL should be a positive natural number")
    
    if ttl <= 0:
        return(False, "TTL should be a positive natural number")
    
    if (key in cache):
        # Key expiry check
        if (not is_expired(key)):
            return (False, "A valid Key already exists")

    # Add a new cache entry as no valid key exists
    cache[key] = (value, datetime.now()+timedelta(seconds=ttl), ttl_sec)
    return (True, "Key and Value successfully added in cache")


def get_cache_item(key):
    global cache

    if key not in cache:
        return (False, "The Key doesn't exist")

    if (is_expired(key)):
        cache.pop(key)
        return (False, "The Key doesn't exist")

    return (True, cache[key][0])


def update_cache_item(key, value, ttl_sec):
    global cache

    try:
        ttl = int(ttl_sec)
    except ValueError: 
        return (False, "TTL should be a positive natural number")
    
    if ttl <= 0:
        return(False, "TTL should be a positive natural number")

    if key not in cache:
        return(False, "The Key doesn't exist")
    
    cache[key] = (value, datetime.now()+timedelta(seconds=ttl), ttl_sec)
    return (1, "Key and Value successfully updated in cache")


def del_cache_item(key):
    global cache

    if key not in cache:
        return(False, "Key is not present in cache")
    
    if (is_expired(key)):
        cache.pop(key)
        return (False, "The Key doesn't exist") 
    
    cache.pop(key)
    return (True, "Key successfully deleted from the cache")


def print_cache_items():
    global cache
    expired_keys = set()

    print(f"In Memory Cache\n")
    for key in cache:
        if is_expired(key):
            expired_keys.add(key)
            continue

        print(f"\t{key} : {cache[key][0]} : {cache[key][2]}\n")

    print(f"END\n")

    for key in expired_keys:
        cache.pop(key)


if __name__ == "__main__":
    cache_status = add_cache_item("name", "Alice", 5)
    print(cache_status)
    print_cache_items()
    cache_status = get_cache_item("name")
    print(cache_status)
    cache_status = update_cache_item("name", "Bob", 10)
    print(cache_status)
    print_cache_items()
    cache_status = del_cache_item("name")
    print(cache_status)
    print_cache_items()    
    cache_status = get_cache_item("name")
    print(cache_status)
    cache_status = add_cache_item("age", "30", 3)
    print(cache_status)
    print_cache_items()
    import time
    time.sleep(4)
    print_cache_items()
    cache_status = get_cache_item("age")
    print(cache_status)
