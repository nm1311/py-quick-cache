from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict


class BaseMetrics(ABC):

    # ---------- Event recording ----------

    @abstractmethod
    def record_set(self):
        pass

    @abstractmethod
    def record_get(self):
        pass

    @abstractmethod
    def record_hit(self):
        pass

    @abstractmethod
    def record_miss(self):
        pass

    @abstractmethod
    def record_failed_op(self):
        pass

    @abstractmethod
    def record_eviction(self):
        pass

    @abstractmethod
    def record_expired_removal(self):
        pass

    @abstractmethod
    def record_manual_deletion(self):
        pass

    @abstractmethod
    def record_manual_deletions(self, count):
        pass

    # ---------- State updates ----------

    @abstractmethod
    def update_total_keys(self, length: int):
        pass

    @abstractmethod
    def update_valid_keys(self, size: int):
        pass

    @abstractmethod
    def update_valid_keys_by_delta(self, delta: int):
        pass

    # ---------- Export / lifecycle ----------

    @abstractmethod
    def snapshot(self) -> dict:
        pass

    @abstractmethod
    def reset(self):
        pass
