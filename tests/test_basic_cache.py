import time
import pytest
import tempfile

from pyquickcache import QuickCacheConfig, QuickCache
from pyquickcache.exceptions import (
    KeyNotFound,
    KeyAlreadyExists,
    KeyExpired,
    InvalidTTL,
    CacheLoadError,
    CacheSaveError,
    CacheMetricsSaveError,
)

"""
def test_pytest_is_working():
    assert (1+2) == 3


def test_cache_can_be_created():
    cache = QuickCache()
    assert cache is not None


def test_add_and_get_value():
    cache = QuickCache()
    cache.add(key="a", value="123", ttl_sec=10)
    value = cache.get(key="a")
    assert value == "123"


def test_get_missing_key_raises_keynotfound():
    cache = QuickCache()

    with pytest.raises(expected_exception=KeyNotFound):
        cache.get("does-not-exist")


def test_delete_missing_key_raises_keynotfound():
    cache = QuickCache()

    with pytest.raises(KeyNotFound):
        cache.delete("missing")



def test_add_existing_key_raises():
    cache = QuickCache()
    cache.set("a", 1)

    with pytest.raises(KeyAlreadyExists):
        cache.add("a", 2)

    # Ensure value was not overwritten
    assert cache.get("a") == 1


def test_update_missing_key_raises_keynotfound():
    cache = QuickCache()

    with pytest.raises(KeyNotFound):
        cache.update(key="missing", value=123)

"""


# ---------------------------------------------------------------------
# Fixture: provides a fresh cache for every test
# ---------------------------------------------------------------------


@pytest.fixture
def cache():
    config = QuickCacheConfig(
        default_ttl=2,
        max_size=10,
        cleanup_interval=0.1,
        enable_metrics=True,
    )
    cache = QuickCache(config)
    yield cache
    cache.stop()


# ---------------------------------------------------------------------
# Basic behavior tests (core public API)
# ---------------------------------------------------------------------


# ---------------------------------------------------------------------
# Basic get and set


def test_set_and_get(cache):
    cache.set("a", 1)
    assert cache.get("a") == 1


def test_get_missing_key_raises(cache):
    with pytest.raises(KeyNotFound):
        cache.get("missing")


# ---------------------------------------------------------------------
# TTL & Expiration


def test_key_expiration(cache):
    cache.set("a", "value", ttl_sec=1)
    time.sleep(1.2)

    with pytest.raises((KeyExpired, KeyNotFound)):
        cache.get("a")


def test_invalid_ttl_raises(cache):
    with pytest.raises(InvalidTTL):
        cache.set("a", 1, ttl_sec=0)


# ---------------------------------------------------------------------
# add


def test_add_new_key(cache):
    cache.add("a", 1)
    assert cache.get("a") == 1


def test_add_existing_key_raises(cache):
    cache.add("a", 1)

    with pytest.raises(KeyAlreadyExists):
        cache.add("a", 2)


# ---------------------------------------------------------------------
# update


def test_update_existing_key(cache):
    cache.set("a", 1)
    cache.update("a", 2)

    assert cache.get("a") == 2


def test_update_missing_key_raises(cache):
    with pytest.raises(KeyNotFound):
        cache.update("missing", 1)


# ---------------------------------------------------------------------
# delete


def test_delete_key(cache):
    cache.set("a", 1)
    cache.delete("a")

    with pytest.raises(KeyNotFound):
        cache.get("a")


# ---------------------------------------------------------------------
# Bulk Operations


def test_set_many(cache):
    cache.set_many({"a": 1, "b": 2})
    assert cache.get("a") == 1
    assert cache.get("b") == 2


def test_get_many(cache):
    cache.set_many({"a": 1, "b": 2})
    result = cache.get_many(["a", "b", "c"])

    assert result == {"a": 1, "b": 2}


def test_delete_many(cache):
    cache.set_many({"a": 1, "b": 2})
    cache.delete_many(["a", "b", "c"])

    assert cache.size() == 0


# ---------------------------------------------------------------------
# Size APIs


def test_size_and_valid_size(cache):
    cache.set("a", 1)
    cache.set("b", 2, ttl_sec=1)

    assert cache.size() == 2
    time.sleep(1.2)

    assert cache.valid_size() == 1


# ---------------------------------------------------------------------
# Clear & Cleanup


def test_clear(cache):
    cache.set_many({"a": 1, "b": 2})
    cache.clear()

    assert cache.size() == 0


def test_cleanup_removes_expired(cache):
    cache.set("a", 1, ttl_sec=1)
    time.sleep(1.2)

    cache.cleanup()
    assert cache.size() == 0


# ---------------------------------------------------------------------
# Metrics APIs


def test_get_metrics_snapshot(cache):
    cache.set("a", 1)
    cache.get("a")

    metrics = cache.get_metrics_snapshot()
    assert "hits" in metrics
    assert metrics["hits"] >= 1


def test_reset_metrics(cache):
    cache.set("a", 1)
    cache.get("a")

    cache.reset_metrics()
    metrics = cache.get_metrics_snapshot()

    assert metrics["hits"] == 0


# ---------------------------------------------------------------------
# Disk Persistence


def test_save_and_load_cache(cache):
    cache.set("a", 1)

    with tempfile.TemporaryDirectory() as tmp:
        path = f"{tmp}/cache"
        cache.save_to_disk(filepath=path)
        cache.clear()

        cache.load_from_disk(filepath=path)
        assert cache.get("a") == 1


def test_save_cache_failure(cache, monkeypatch):
    def bad_write(*args, **kwargs):
        raise IOError("boom")

    monkeypatch.setattr(cache.cache_file_manager, "write", bad_write)

    with pytest.raises(CacheSaveError):
        cache.save_to_disk()


# ---------------------------------------------------------------------
# Metrics Persistence


def test_save_metrics_to_disk(cache):
    cache.set("a", 1)

    with tempfile.TemporaryDirectory() as tmp:
        path = f"{tmp}/metrics"
        cache.save_metrics_to_disk(filepath=path)


def test_save_metrics_failure(cache, monkeypatch):
    def bad_write(*args, **kwargs):
        raise IOError("boom")

    monkeypatch.setattr(cache.cache_metrics_file_manager, "write", bad_write)

    with pytest.raises(CacheMetricsSaveError):
        cache.save_metrics_to_disk()


# ---------------------------------------------------------------------
# Misc


def test_repr(cache):
    r = repr(cache)
    assert "QuickCache" in r


def test_stop_is_idempotent(cache):
    cache.stop()
    cache.stop()  # should not raise
