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

class KeyAlreadyExists(CacheError):
    code = "KEY_ALREADY_EXISTS"

    def __init__(self, key: str):
        super().__init__(f"Key '{key}' already exists")
        self.key = key


class InvalidTTL(CacheError):
    code = "INVALID_TTL"

    def __init__(self, ttl: int):
        super().__init__(f"Invalid TTL value: {ttl}")
        self.ttl = ttl


class CacheSaveError(CacheError):
    code = "CACHE_SAVE_ERROR"

    def __init__(self, filepath: str, original_exception: Exception | None = None):
        message = f"Failed to save cache to disk: {filepath}"
        if original_exception:
            message += f" | {original_exception}"
        super().__init__(message)
        self.filepath = filepath
        self.original_exception = original_exception


class CacheLoadError(CacheError):
    code = "CACHE_LOAD_ERROR"

    def __init__(self, filepath: str, original_exception: Exception | None = None):
        message = f"Failed to load cache from disk: {filepath}"
        if original_exception:
            message += f" | {original_exception}"
        super().__init__(message)
        self.filepath = filepath
        self.original_exception = original_exception


class CacheMetricsSaveError(CacheError):
    code = "CACHE_METRICS_SAVE_ERROR"

    def __init__(self, filepath: str, cause: Exception | None = None):
        super().__init__(f"Failed to save cache metrics to disk: {filepath}")
        self.filepath = filepath
        self.__cause__ = cause
