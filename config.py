from dataclasses import dataclass


@dataclass
class CacheConfig:
    max_size: int = 3
    default_ttl: int = 5
    cleanup_interval: int = 2

    storage_dir: str = "cache_storage"
    filename: str = "cache_data"

    eviction_policy: str = "lru"
    serializer: str = "pickle"
    enable_metrics: bool = False
