from dataclasses import dataclass


@dataclass
class QuickCacheConfig:
    """
    Configuration class for QuickCache.

    This dataclass holds all configurable parameters for the cache, including
    size limits, TTLs, storage options, serializer preferences, eviction policy,
    and metrics settings.

    Attributes:
        max_size (int): Maximum number of items allowed in the cache.
        default_ttl (int): Default time-to-live (TTL) for cache entries in seconds.
        cleanup_interval (int): Interval in seconds to perform automatic cleanup of expired entries.

        serializer (str): Name of the serializer to use for storing cache data. Default is 'pickle'.
        eviction_policy (str): Eviction policy to use when cache exceeds max_size. Default is 'lru'.

        storage_dir (str): Directory where cache files are stored. Default is 'cache_storage'.
        filename (str): Name of the file to store cache data. Default is 'cache_data'.
        cache_timestamps (bool): Whether to store timestamps for cache entries. Default is False.

        enable_metrics (bool): Whether to enable metrics tracking. Default is True.
        metrics_serializer (str): Serializer for metrics data. Default is 'json'.
        metrics_storage_dir (str): Directory to store metrics files. Default is 'cache_metrics'.
        metrics_filename (str): Filename for metrics storage. Default is 'metrics'.
        cache_metrics_timestamps (bool): Whether to store timestamps for metrics entries. Default is False.
    """

    max_size: int = 50
    default_ttl: int = 500
    cleanup_interval: int = 50

    eviction_policy: str = "lru"
    serializer: str = "pickle"

    storage_dir: str = "cache_storage"
    filename: str = "cache_data"
    cache_timestamps: bool = False

    enable_metrics: bool = True
    metrics_serializer: bool = "json"
    metrics_storage_dir: str = "cache_metrics"
    metrics_filename: str = "metrics"
    cache_metrics_timestamps: bool = False
