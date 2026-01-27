from time import time
from pyquickcache import QuickCache
import time
from pprint import pprint

if __name__ == "__main__":
    my_cache = QuickCache()

    # Loading from disk if available
    status = my_cache.load_from_disk(filepath="cache_storage/cache_data.json")
    print(status)
    my_cache._debug_print()
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
    my_cache._debug_print()
    status = my_cache.get("city")
    print(status)
    status = my_cache.update("city", "Los Angeles", 1000)
    print(status)
    my_cache._debug_print()
    status = my_cache.delete("city")
    print(status)
    status = my_cache.size()
    print(f"Cache Size: {status}")
    my_cache._debug_print()
    status = my_cache.get("city")
    print(status)
    status = my_cache.add("country", "USA", 300)
    print(status)
    my_cache._debug_print()
    time.sleep(4)
    status = my_cache.cleanup()
    print(status)
    my_cache._debug_print()
    status = my_cache.get("country")
    print(status)

    # --- TESTING BULK OPERATIONS ---
    print("\n" + "=" * 30)
    print("TESTING BULK OPERATIONS")
    print("=" * 30)

    # 1. Testing set_many (Upsert Logic)
    # We will add some new keys and overwrite one existing key (city1)
    bulk_data = {
        "city1": "New Delhi",  # Update
        "city5": "Bangalore",  # New
        "city6": "Chennai",  # New
        "city7": "Hyderabad",  # New (This might trigger eviction if max_size is small)
    }
    print(f"\nPerforming set_many with {list(bulk_data.keys())}...")
    status = my_cache.set_many(
        data=bulk_data, ttl_sec=2
    )  # Short TTL for testing ghosts
    print(f"Status: {status.message} | Details: {status.data}")
    my_cache._debug_print()

    # 2. Testing get_many (Hit/Miss/Ghost Logic)
    # city1 is valid, city100 doesn't exist
    keys_to_get = ["city1", "city5", "city100"]
    print(f"\nPerforming get_many for {keys_to_get}...")
    results = my_cache.get_many(keys_to_get)
    print(f"Results found: {results}")

    # 3. Testing Ghost Handling in get_many
    print("\nWaiting for items to expire (3 seconds)...")
    time.sleep(3)

    # city1 and city5 are now ghosts. get_many should return empty and record misses.
    print(f"Performing get_many for {keys_to_get} after expiration...")
    results_after_expiry = my_cache.get_many(keys_to_get)
    print(f"Results found (should be empty): {results_after_expiry}")

    # 4. Testing delete_many
    # Let's add fresh data and then delete a subset
    my_cache.set_many({"alpha": 1, "beta": 2, "gamma": 3})
    print("\nCache before delete_many:")
    my_cache._debug_print()

    keys_to_delete = ["alpha", "gamma", "non_existent"]
    print(f"Deleting {keys_to_delete}...")
    # If you haven't implemented delete_many yet, this is where you'd call it
    status = my_cache.delete_many(keys_to_delete)
    print(status)

    # 5. Testing clear
    # print("\nClearing entire cache...")
    # status = my_cache.clear()
    # print(status)

    # Final Metrics Check
    print("\nFinal Metrics Snapshot:")
    import pprint

    pprint.pprint(my_cache.get_metrics_snapshot())

    # Save to disk
    status = my_cache.save_to_disk()
    print(status)

    print(my_cache.get_metrics_snapshot())

    status = my_cache.save_metrics_to_disk()
    print(status)
