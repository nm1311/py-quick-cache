from typing import Type, Dict
from eviction_policy import EvictionPolicy
from serializer import BaseSerializer

_EVICTION_POLICY_REGISTRY: Dict[str, Type[EvictionPolicy]] = {}
_SERIALIZER_REGISTRY: Dict[str, Type[BaseSerializer]] = {}


def register_eviction_policy(name: str, cls: Type[EvictionPolicy]) -> None:
    key = name.lower()
    if key in _EVICTION_POLICY_REGISTRY:
        raise ValueError(f"Eviction policy '{name}' already registered.")

    if not issubclass(cls, EvictionPolicy):
        raise TypeError("Eviction policy must inherit from EvictionPolicy.")

    _EVICTION_POLICY_REGISTRY[key] = cls


def register_serializer(name: str, cls: Type[BaseSerializer]) -> None:
    key = name.lower()
    if key in _SERIALIZER_REGISTRY:
        raise ValueError(f"Serializer '{name}' already registered.")

    if not issubclass(cls, BaseSerializer):
        raise TypeError("Serializer must inherit from BaseSerializer.")

    _SERIALIZER_REGISTRY[key] = cls


def create_eviction_policy(name: str) -> EvictionPolicy:
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
    try:
        return _SERIALIZER_REGISTRY[name.lower()]()
    except KeyError:
        raise ValueError(
            f"Unknown serializer '{name}'. "
            f"Available: {list(_SERIALIZER_REGISTRY.keys())}"
        )
