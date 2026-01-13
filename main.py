from time import time
from cache import InMemoryCache
import time

if __name__ == "__main__":
    my_cache = InMemoryCache()

    # Loading from disk if available
    status = my_cache.load_from_disk(filepath="cache_data/cache")
    print(status)
    my_cache.print()
    time.sleep(2)

    status = my_cache.add("city1", "Delhi", 500)
    print(status)
    status = my_cache.add("city2", "Mumbai", 500)
    print(status)
    status = my_cache.add("city3", "Pune", 500)
    print(status)
    status = my_cache.add("city4", "Kolkata", 500)
    print(status)
    status = my_cache.size()
    print(f"Cache Size: {status}")
    my_cache.print()
    status = my_cache.get("city")
    print(status)
    status = my_cache.update("city", "Los Angeles", 1000)
    print(status)
    my_cache.print()
    status = my_cache.delete("city")
    print(status)
    status = my_cache.size()
    print(f"Cache Size: {status}")
    my_cache.print()
    status = my_cache.get("city")
    print(status)
    status = my_cache.add("country", "USA", 300)
    print(status)
    my_cache.print()
    time.sleep(4)
    status = my_cache.cleanup()
    print(status)
    my_cache.print()
    status = my_cache.get("country")
    print(status)


    # Save to disk
    status = my_cache.save_to_disk(filepath="cache_data/cache",use_timestamp=False)
    print(status)


