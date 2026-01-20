from pyquickcache import QuickCacheConfig, QuickCache


def test_add_and_get_basic_value():
    cache = QuickCache()
    resp = cache.add("")
