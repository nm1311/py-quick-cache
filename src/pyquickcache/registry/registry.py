"""
Registry utilities for eviction policies and serializers.

This module provides a lightweight plugin registry that allows
eviction policies and serializers to be registered by name and
instantiated dynamically at runtime.

It enables:
    - Decoupling core cache logic from concrete implementations
    - User-extensible eviction and serialization strategies
    - Configuration-driven component selection

Registries are keyed by lowercase string identifiers to ensure
case-insensitive lookups.
"""

from __future__ import annotations

from typing import Type, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from ..backend import BaseCacheBackend
    from ..eviction_policy import BaseEvictionPolicy
    from ..serializer import BaseSerializer

# Global registries for pluggable components
_CACHE_BACKEND_REGISTRY = Dict[str, Type[BaseCacheBackend]] = {}
_EVICTION_POLICY_REGISTRY: Dict[str, Type[BaseEvictionPolicy]] = {}
_SERIALIZER_REGISTRY: Dict[str, Type[BaseSerializer]] = {}

def _register_cache_backend(name: str, cls: Type[BaseCacheBackend]) -> None:
    """
    Register a cache backend class under a human-readable name.

    This function associates a unique string identifier with a concrete
    backend implementation. The name is normalized to lowercase to allow
    case-insensitive lookups when creating a backend dynamically.

    Args:
        name (str): Unique name identifying the backend.
        cls (Type[BaseCacheBackend]): The backend class to register. Must
            be a subclass of BaseCacheBackend.

    Raises:
        ValueError: If a backend with the same name has already been registered.

    Example:
        _register_backend("file", FileBackend)
    """

    key = name.lower()
    if key in _CACHE_BACKEND_REGISTRY:
        raise ValueError(f"Cache backend '{name}' already registered.")
    _CACHE_BACKEND_REGISTRY[key] = cls



def _register_eviction_policy(name: str, cls: Type[BaseEvictionPolicy]) -> None:
    """
    Register an eviction policy implementation.

    This function associates a human-readable name with a concrete
    eviction policy class. The name is stored in lowercase to ensure
    case-insensitive lookups.

    Args:
        name (str): Unique name identifying the eviction policy.
        cls (Type[BaseEvictionPolicy]): Eviction policy class to register.

    Raises:
        ValueError: If an eviction policy with the same name
            is already registered.

    Example:
        register_eviction_policy("lru", LRUEvictionPolicy)
    """

    key = name.lower()
    if key in _EVICTION_POLICY_REGISTRY:
        raise ValueError(f"Eviction policy '{name}' already registered.")
    _EVICTION_POLICY_REGISTRY[key] = cls


def _register_serializer(name: str, cls: Type[BaseSerializer]) -> None:
    """
    Register a serializer implementation.

    This function associates a human-readable name with a concrete
    serializer class. The name is stored in lowercase to ensure
    case-insensitive lookups.

    Args:
        name (str): Unique name identifying the serializer.
        cls (Type[BaseSerializer]): Serializer class to register.

    Raises:
        ValueError: If a serializer with the same name
            is already registered.

    Example:
        register_serializer("json", JsonSerializer)
    """

    key = name.lower()
    if key in _SERIALIZER_REGISTRY:
        raise ValueError(f"Serializer '{name}' already registered.")
    _SERIALIZER_REGISTRY[key] = cls


def create_cache_backend(name: str) -> BaseCacheBackend:
    """
        Instantiate a registered cache backend by name.

        This function looks up the backend class registered under the
        given name and returns a new instance. Names are matched
        case-insensitively.

        Args:
            name (str): Name of the backend to instantiate.

        Returns:
            BaseCacheBackend: A new instance of the requested backend.

        Raises:
            ValueError: If no backend is registered under the given name.

        Example:
            backend = create_cache_backend("file")
        """
    try:
        return _CACHE_BACKEND_REGISTRY[
            name.lower()
        ]()  # end parenthesis to return a class object
    except:
        raise ValueError(
            f"Unknown cache backend '{name}'. "
            f"Available: {list(_CACHE_BACKEND_REGISTRY.keys())}"
        )



def create_eviction_policy(name: str) -> BaseEvictionPolicy:
    """
    Instantiate a registered eviction policy by name.

    This function looks up the eviction policy class registered
    under the given name and returns a new instance.

    Args:
        name (str): Name of the eviction policy to instantiate.

    Returns:
        BaseEvictionPolicy: A new eviction policy instance.

    Raises:
        ValueError: If no eviction policy is registered under
            the given name.

    Example:
        policy = create_eviction_policy("lru")
    """

    try:
        return _EVICTION_POLICY_REGISTRY[
            name.lower()
        ]()  # end parenthesis to return a class object
    except:
        raise ValueError(
            f"Unknown eviction policy '{name}'. "
            f"Available: {list(_EVICTION_POLICY_REGISTRY.keys())}"
        )


def create_serializer(name: str) -> BaseSerializer:
    """
    Instantiate a registered serializer by name.

    This function looks up the serializer class registered
    under the given name and returns a new instance.

    Args:
        name (str): Name of the serializer to instantiate.

    Returns:
        BaseSerializer: A new serializer instance.

    Raises:
        ValueError: If no serializer is registered under
            the given name.

    Example:
        serializer = create_serializer("json")
    """

    try:
        return _SERIALIZER_REGISTRY[name.lower()]()
    except KeyError:
        raise ValueError(
            f"Unknown serializer '{name}'. "
            f"Available: {list(_SERIALIZER_REGISTRY.keys())}"
        )
