import time
from pprint import pprint

from pyquickcache import QuickCache
from pyquickcache.exceptions import (
    KeyNotFound,
    KeyExpired,
)

cache = QuickCache()


def run_test(label: str, fn):
    print(f"\n▶ {label}")
    try:
        fn()
        print("✅ PASSED")
    except Exception as e:
        print(f"❌ FAILED: {type(e).__name__} → {e}")


def test_load():
    # Treat missing file as non-fatal
    try:
        cache.load_from_disk("cache_storage/cache_data.json")
    except FileNotFoundError:
        print("ℹ️ No cache file found, starting fresh")


def test_add():
    cache.add("city1", "Delhi", ttl_sec=5)
    cache.add("city2", "Mumbai", ttl_sec=5)


def test_get_missing():
    try:
        cache.get("missing")
    except KeyNotFound:
        print("✔️ Expected KeyNotFound")


def test_update():
    cache.update("city1", "New Delhi", ttl_sec=10)


def test_expiry():
    cache.add("temp", "value", ttl_sec=1)
    time.sleep(2)
    try:
        cache.get("temp")
    except KeyExpired:
        print("✔️ Expected expiration")


def test_bulk():
    cache.set_many({"a": 1, "b": 2}, ttl_sec=2)
    results = cache.get_many(["a", "b", "c"])
    print("Results:", results)


def test_metrics():
    pprint(cache.get_metrics_snapshot())


# -------------------------------
# Run all tests
# -------------------------------
run_test("Load from disk", test_load)
run_test("Add entries", test_add)
run_test("Get missing key", test_get_missing)
run_test("Update entry", test_update)
run_test("Expiry handling", test_expiry)
run_test("Bulk ops", test_bulk)
run_test("Metrics snapshot", test_metrics)

print("\n🏁 Finished all tests")
