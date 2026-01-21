"""

import pytest

from pyquickcache import QuickCacheConfig, QuickCache


@pytest.fixture
def cache():
    config = QuickCacheConfig(
        max_size=100,
        default_ttl=5,
        cleanup_interval=3600,  # effectively disable background cleanup
        enable_metrics=False,
    )

    cache = QuickCache(config=config)
    yield cache
    cache.stop()


"""
