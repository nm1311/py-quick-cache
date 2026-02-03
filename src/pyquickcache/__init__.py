"""
pyquickcache

A fast, extensible in-memory caching library with TTL support,
pluggable eviction policies, persistence, and metrics.

This package exposes the public caching API.
"""

# Trigger registration of built-in backends, serializers & eviction policies
from ._bootstrap import *

from .quick_cache import QuickCache
from .quick_cache_config import QuickCacheConfig
from .decorators import register_eviction_policy, register_serializer

__all__ = [
    "QuickCache",
    "QuickCacheConfig",
    "register_eviction_policy",
    "register_serializer",
]
