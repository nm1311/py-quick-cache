"""
Bootstrap module for cache registries.

This module initializes and exposes the core registry packages for
serializers and eviction policies. Importing this module ensures that
all serializers and eviction policies are registered and available for use.

Modules Imported:
    - serializer: Exposes all registered serializers.
    - eviction_policy: Exposes all registered eviction policies.

INTERNAL:
    Used internally to bootstrap the registry system. Users typically do
    not need to import this directly.
"""

from . import backend
from . import eviction_policy
from . import serializer
