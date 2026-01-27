from typing import Type

from .registry import (
    register_eviction_policy as _register_eviction_policy,
    register_serializer as _register_serializer,
)


def register_eviction_policy(name: str):
    """
    Class decorator to register a custom eviction policy.

    Args:
    name (str): Policy identifier used in cache configuration.

    Example:
    @register_eviction_policy("my_policy")
    class MyPolicy(BaseEvictionPolicy):

    """
    # It is done to avoid circular imports
    from ..eviction_policy.base_eviction_policy import BaseEvictionPolicy

    def decorator(cls: Type[BaseEvictionPolicy]) -> Type[BaseEvictionPolicy]:
        if not issubclass(cls, BaseEvictionPolicy):
            raise TypeError(
                f"Eviction policy must inherit from BaseEvictionPolicy, got {cls.__name__}"
            )

        _register_eviction_policy(name, cls)
        return cls

    return decorator


def register_serializer(name: str):
    """
    Class decorator to register a custom serializer.

    Args:
    name (str): Serializer identifier used in cache configuration.

    Example:
    @register_serializer("yaml")
    class YamlSerializer(BaseSerializer):

    """
    # It is done to avoid circular imports
    from ..serializer.base_serializer import BaseSerializer

    def decorator(cls: Type[BaseSerializer]) -> Type[BaseSerializer]:
        if not issubclass(cls, BaseSerializer):
            raise TypeError(
                f"Serializer must inherit from BaseSerializer, got {cls.__name__}"
            )

        _register_serializer(name, cls)
        return cls

    return decorator
