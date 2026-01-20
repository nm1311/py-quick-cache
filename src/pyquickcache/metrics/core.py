from .base import BaseMetrics
from dataclasses import dataclass, asdict


@dataclass
class CacheMetricsData:
    hits: int = 0
    misses: int = 0
    sets: int = 0
    gets: int = 0
    failed_ops: int = 0
    evictions: int = 0
    expired_removals: int = 0
    manual_deletions: int = 0
    current_valid_keys: int = 0
    peak_valid_keys: int = 0
    current_total_keys: int = 0
    peak_total_keys: int = 0

    # --- Calculated Properties ---

    @property
    def hit_ratio(self) -> float:
        return (self.hits / self.gets) if self.gets > 0 else 0.0

    @property
    def miss_ratio(self) -> float:
        return (self.misses / self.gets) if self.gets > 0 else 0.0

    @property
    def get_set_ratio(self) -> float:
        return (self.gets / self.sets) if self.sets > 0 else 0.0

    @property
    def eviction_rate(self) -> float:
        return (self.evictions / self.sets) if self.sets > 0 else 0.0

    @property
    def expired_bloat(self) -> int:
        return self.current_total_keys - self.current_valid_keys

    @property
    def waste_percentage(self) -> float:
        return (
            (self.expired_bloat / self.current_total_keys * 100)
            if self.current_total_keys > 0
            else 0.0
        )

    def to_dict(self):
        data = asdict(self)

        data.update(
            {
                "hit_ratio": self.hit_ratio,
                "miss_ratio": self.miss_ratio,
                "get_set_ratio": self.get_set_ratio,
                "eviction_rate": self.eviction_rate,
                "expired_bloat": self.expired_bloat,
                "waste_percentage": self.waste_percentage,
            }
        )

        return data


class CacheMetrics(BaseMetrics):
    def __init__(self):
        self._data = CacheMetricsData()

    @property
    def hits(self) -> int:
        return self._data.hits

    @property
    def misses(self) -> int:
        return self._data.misses

    @property
    def gets(self) -> int:
        return self._data.gets

    @property
    def sets(self) -> int:
        return self._data.sets

    @property
    def failed_ops(self) -> int:
        return self._data.failed_ops

    @property
    def evictions(self) -> int:
        return self._data.evictions

    @property
    def expired_removals(self) -> int:
        return self._data.expired_removals

    @property
    def manual_deletions(self) -> int:
        return self._data.manual_deletions

    @property
    def current_valid_keys(self) -> int:
        return self._data.current_valid_keys

    @property
    def peak_valid_keys(self) -> int:
        return self._data.peak_valid_keys

    @property
    def current_total_keys(self) -> int:
        return self._data.current_total_keys

    @property
    def peak_total_keys(self) -> int:
        return self._data.peak_total_keys

    @property
    def hit_ratio(self) -> float:
        return self._data.hit_ratio

    @property
    def miss_ratio(self) -> float:
        return self._data.miss_ratio

    @property
    def get_set_ratio(self) -> float:
        return self._data.get_set_ratio

    @property
    def eviction_rate(self) -> float:
        return self._data.eviction_rate

    @property
    def expired_bloat(self) -> int:
        return self._data.expired_bloat

    @property
    def waste_percentage(self) -> float:
        return self._data.waste_percentage

    def record_set(self):
        self._data.sets += 1

    def record_hit(self):
        self._data.hits += 1

    def record_miss(self):
        self._data.misses += 1

    def record_failed_op(self):
        self._data.failed_ops += 1

    def record_get(self):
        self._data.gets += 1

    def record_eviction(self):
        self._data.evictions += 1

    def record_expired_removal(self):
        self._data.expired_removals += 1

    def record_manual_deletion(self):
        self._data.manual_deletions += 1

    def record_manual_deletions(self, count):
        self._data.manual_deletions += count

    def update_total_keys(self, length: int):
        self._data.current_total_keys = length
        if self._data.current_total_keys > self._data.peak_total_keys:
            self._data.peak_total_keys = self._data.current_total_keys

    # RENAME TO update_valid_size
    def update_valid_keys(self, size: int):
        self._data.current_valid_keys = size
        if size > self._data.peak_valid_keys:
            self._data.peak_valid_keys = size

    def update_valid_keys_by_delta(self, delta: int):
        new_value = self._data.current_valid_keys + delta
        self._data.current_valid_keys = max(0, new_value)

        if self._data.current_valid_keys > self._data.peak_valid_keys:
            self._data.peak_valid_keys = self._data.current_valid_keys

    def snapshot(self):
        """Return current metrics as a serializable dictionary."""
        snapshot = self._data.to_dict()
        return snapshot

    def reset(self):
        self._data = CacheMetricsData()
