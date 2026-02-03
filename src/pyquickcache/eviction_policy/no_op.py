from collections import OrderedDict
from .base import BaseEvictionPolicy

from ..registry.decorators import register_eviction_policy


@register_eviction_policy("no_op")
class NoOpEvictionPolicy(BaseEvictionPolicy):
    """
    No operation eviction policy.

    INTERNAL:
        Subclasses BaseEvictionPolicy and implements required lifecycle methods.
    """

    def on_add(self, cache, key) -> None:
        """
        Do nothing
        """
        pass

    def on_update(self, cache: OrderedDict, key: str) -> None:
        """
        Do nothing
        """
        pass

    def on_access(self, cache: OrderedDict, key: str) -> None:
        """
        Do nothing
        """
        pass

    def on_delete(self, cache, key) -> None:
        """
        Do nothing
        """
        pass

    def select_eviction_key(self, cache: OrderedDict) -> str:
        """
        No-operation eviction policy.

        This policy performs no eviction and is intended for backends
        that manage eviction internally (e.g., Redis) or do not support
        eviction.

        INTERNAL:
            Implements the BaseEvictionPolicy interface without modifying
            cache state.
        """
        raise RuntimeError(
            "Eviction requested but NoOpEvictionPolicy is in use. "
            "This backend is expected to manage eviction itself."
        )
