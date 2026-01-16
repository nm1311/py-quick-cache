from .base import BaseMetrics


class NoOpMetrics(BaseMetrics):
    def record_set(self):
        pass

    def record_get(self):
        pass

    def record_hit(self):
        pass

    def record_miss(self):
        pass

    def record_failed_op(self):
        pass

    def record_eviction(self):
        pass

    def record_expired_removal(self):
        pass

    def record_manual_deletion(self):
        pass

    def update_total_keys(self, length: int):
        pass

    def update_valid_keys(self, size: int):
        pass

    def update_valid_keys_by_delta(self, delta: int):
        pass

    def snapshot(self) -> dict:
        return {}

    def reset(self):
        pass
