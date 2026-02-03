import pytest

from pyquickcache import QuickCache, QuickCacheConfig
from pyquickcache.exceptions import KeyNotFound

# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------


def make_cache(eviction_policy: str):
    config = QuickCacheConfig(
        max_size=2,
        default_ttl=60,
        eviction_policy=eviction_policy,
        cleanup_interval=0,
    )
    return QuickCache(config)


# ---------------------------------------------------------------------
# LRU (Least Recently Used)
# ---------------------------------------------------------------------


def test_lru_eviction():
    cache = make_cache("lru")

    cache.set("a", 1)
    cache.set("b", 2)

    # Access 'a' so 'b' becomes least recently used
    cache.get("a")

    # This should evict 'b'
    cache.set("c", 3)

    assert cache.get("a") == 1
    assert cache.get("c") == 3

    with pytest.raises(KeyNotFound):
        cache.get("b")


# ---------------------------------------------------------------------
# FIFO (First In First Out)
# ---------------------------------------------------------------------


def test_fifo_eviction():
    cache = make_cache("fifo")

    cache.set("a", 1)
    cache.set("b", 2)

    # FIFO evicts the first inserted key: 'a'
    cache.set("c", 3)

    assert cache.get("b") == 2
    assert cache.get("c") == 3

    with pytest.raises(KeyNotFound):
        cache.get("a")


# ---------------------------------------------------------------------
# LFU (Least Frequently Used)
# ---------------------------------------------------------------------


def test_lfu_eviction():
    cache = make_cache("lfu")

    cache.set("a", 1)
    cache.set("b", 2)

    # Increase frequency of 'a'
    cache.get("a")
    cache.get("a")

    # 'b' has lower frequency → should be evicted
    cache.set("c", 3)

    assert cache.get("a") == 1
    assert cache.get("c") == 3

    with pytest.raises(KeyNotFound):
        cache.get("b")


# ---------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------


def test_eviction_policy_respects_max_size():
    cache = make_cache("lru")

    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("c", 3)

    assert cache.size() == 2


def test_eviction_does_not_break_cache():
    cache = make_cache("fifo")

    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("c", 3)
    cache.set("d", 4)

    assert cache.size() == 2
