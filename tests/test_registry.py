import pytest

from pyquickcache.decorators import (
    register_eviction_policy,
    register_serializer,
)
from pyquickcache.registry.registry import (
    create_eviction_policy,
    create_serializer,
)
from pyquickcache.eviction_policy import BaseEvictionPolicy
from pyquickcache.serializer import BaseSerializer

# ---------------------------------------------------------------------
# Eviction Policy Registration (Decorator-based)
# ---------------------------------------------------------------------


@register_eviction_policy("decorator_policy")
class DecoratorEvictionPolicy(BaseEvictionPolicy):
    """Test eviction policy registered via decorator."""

    def on_add(self, cache, key):
        pass

    def on_update(self, cache, key):
        pass

    def on_access(self, cache, key):
        pass

    def on_delete(self, cache, key):
        pass

    def select_eviction_key(self, cache):
        if not cache:
            raise RuntimeError("Eviction requested on empty cache")
        return next(iter(cache))


def test_eviction_policy_registered_via_decorator():
    policy = create_eviction_policy("decorator_policy")
    assert isinstance(policy, DecoratorEvictionPolicy)


def test_duplicate_eviction_policy_registration_raises():
    with pytest.raises(ValueError):

        @register_eviction_policy("decorator_policy")
        class DuplicateEvictionPolicy(BaseEvictionPolicy):
            def on_add(self, cache, key):
                pass

            def on_update(self, cache, key):
                pass

            def on_access(self, cache, key):
                pass

            def on_delete(self, cache, key):
                pass

            def select_eviction_key(self, cache):
                return None


def test_invalid_eviction_policy_base_raises():
    with pytest.raises(TypeError):

        @register_eviction_policy("invalid_policy")
        class NotAnEvictionPolicy:
            pass


def test_unknown_eviction_policy_raises():
    with pytest.raises(ValueError):
        create_eviction_policy("unknown_policy")


# ---------------------------------------------------------------------
# Serializer Registration (Decorator-based)
# ---------------------------------------------------------------------


@register_serializer("decorator_serializer")
class DecoratorSerializer(BaseSerializer):
    """Test serializer registered via decorator."""

    @property
    def extension(self):
        return "txt"

    @property
    def is_binary(self):
        return False

    def serialize(self, data):
        return str(data)

    def deserialize(self, data):
        return data


def test_serializer_registered_via_decorator():
    serializer = create_serializer("decorator_serializer")
    assert isinstance(serializer, DecoratorSerializer)


def test_duplicate_serializer_registration_raises():
    with pytest.raises(ValueError):

        @register_serializer("decorator_serializer")
        class DuplicateSerializer(BaseSerializer):
            @property
            def extension(self):
                return "txt"

            @property
            def is_binary(self):
                return False

            def serialize(self, data):
                return data

            def deserialize(self, data):
                return data


def test_invalid_serializer_base_raises():
    with pytest.raises(TypeError):

        @register_serializer("invalid_serializer")
        class NotASerializer:
            pass


def test_unknown_serializer_raises():
    with pytest.raises(ValueError):
        create_serializer("unknown_serializer")
