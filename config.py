from dataclasses import dataclass


@dataclass
class CacheConfig:
    max_size: int = 3
    default_ttl: int = 5
    cleanup_interval: int = 2

    serializer: str = "pickle"
    storage_dir: str = "cache_storage"
    filename: str = "cache_data"
    cache_timestamps: bool = False

    eviction_policy: str = "lru"

    enable_metrics: bool = True
    metrics_serializer: bool = "json"
    metrics_storage_dir: str = "cache_metrics"
    metrics_filename: str = "metrics"
    cache_metrics_timestamps: bool = False
