import tempfile
import pytest

from pyquickcache import QuickCache, QuickCacheConfig
from pyquickcache.exceptions import KeyNotFound, CacheSaveError

# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------


def make_cache(serializer: str):
    config = QuickCacheConfig(
        serializer=serializer,
        default_ttl=60,
        cleanup_interval=0,
    )
    return QuickCache(config)


# ---------------------------------------------------------------------
# JSON Serializer
# ---------------------------------------------------------------------


def test_json_serializer_save_and_load():
    cache = make_cache("json")

    cache.set("a", {"city": "Delhi", "population": 30})
    cache.set("b", [1, 2, 3])

    with tempfile.TemporaryDirectory() as tmp:
        path = f"{tmp}/cache_json"

        cache.save_to_disk(filepath=path)
        cache.clear()

        with pytest.raises(KeyNotFound):
            cache.get("a")

        cache.load_from_disk(filepath=path)

        assert cache.get("a") == {"city": "Delhi", "population": 30}
        assert cache.get("b") == [1, 2, 3]


def test_json_serializer_handles_primitives():
    cache = make_cache("json")

    cache.set("int", 1)
    cache.set("str", "hello")
    cache.set("bool", True)

    with tempfile.TemporaryDirectory() as tmp:
        path = f"{tmp}/cache_json_primitives"

        cache.save_to_disk(filepath=path)
        cache.clear()
        cache.load_from_disk(filepath=path)

        assert cache.get("int") == 1
        assert cache.get("str") == "hello"
        assert cache.get("bool") is True


# ---------------------------------------------------------------------
# Pickle Serializer
# ---------------------------------------------------------------------


def test_pickle_serializer_save_and_load():
    cache = make_cache("pickle")

    cache.set("a", {"x": 1, "y": [1, 2, 3]})
    cache.set("b", ("tuple", 42))

    with tempfile.TemporaryDirectory() as tmp:
        path = f"{tmp}/cache_pickle"

        cache.save_to_disk(filepath=path)
        cache.clear()

        with pytest.raises(KeyNotFound):
            cache.get("a")

        cache.load_from_disk(filepath=path)

        assert cache.get("a") == {"x": 1, "y": [1, 2, 3]}
        assert cache.get("b") == ("tuple", 42)


# Dummy custom object to be pickled by a test
# We need to define it outside the test since pickle cannot serialize local objects
class Dummy:
    def __init__(self, value):
        self.value = value

    def __eq__(self, other):
        return isinstance(other, Dummy) and self.value == other.value


def test_pickle_serializer_handles_custom_objects():
    cache = make_cache("pickle")

    obj = Dummy(123)
    cache.set("obj", obj)

    with tempfile.TemporaryDirectory() as tmp:
        path = f"{tmp}/cache_pickle_obj"
        cache.save_to_disk(filepath=path)
        cache.clear()
        cache.load_from_disk(filepath=path)

        assert cache.get("obj") == obj


def test_pickle_serializer_rejects_unpicklable_objects():
    cache = make_cache("pickle")

    class Dummy:
        def __init__(self, x):
            self.x = x

    cache.set("obj", Dummy(1))

    with pytest.raises(CacheSaveError):
        cache.save_to_disk()


# ---------------------------------------------------------------------
# Serializer selection
# ---------------------------------------------------------------------


def test_unknown_serializer_raises():
    with pytest.raises(ValueError):
        QuickCache(
            QuickCacheConfig(
                serializer="does_not_exist",
            )
        )
