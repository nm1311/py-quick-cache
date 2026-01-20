class CacheError(Exception):
    """Base class for all cache-related errors."""

    code = "CACHE_ERROR"

    def __init__(self, message: str | None = None):
        super().__init__(message or self.__class__.__name__)
        self.message = message or self.__class__.__name__


class KeyNotFound(CacheError):
    code = "KEY_NOT_FOUND"

    def __init__(self, key: str):
        super().__init__(f"Key '{key}' not found")
        self.key = key


class KeyExpired(CacheError):
    code = "KEY_EXPIRED"

    def __init__(self, key: str):
        super().__init__(f"Key '{key}' has expired")
        self.key = key


class InvalidTTL(CacheError):
    code = "INVALID_TTL"

    def __init__(self, ttl: int):
        super().__init__(f"Invalid TTL value: {ttl}")
        self.ttl = ttl
