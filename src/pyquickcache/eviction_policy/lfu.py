from collections import OrderedDict
from .base_eviction_policy import EvictionPolicy


class LFUEvictionPolicy(EvictionPolicy):
    """
    - Least Frequently Used (LFU) Eviction Policy.
    - Evicts the least frequently used item when the cache is full.
    - A cache item is counted as used when it gets added, updated, set, get or accessed. On deleted the frequency is set removed
    - In case of a tie (multiple items with the same frequency), least recently used item is deleted. (LFU + LRU)
    """

    def __init__(self):
        # keys -> frequency
        self.freq: dict[str, int] = {}

        # frequemcy -> ordered keys
        self.freq_table: dict[int, OrderedDict[str, None]] = {}

        # track current minimum frequency
        self.min_freq: int = 0

    def on_add(self, cache, key) -> None:
        frequency = 1

        # Track frequency
        self.freq[key] = frequency

        # Ensure bucket exists
        if frequency not in self.freq_table:
            self.freq_table[frequency] = OrderedDict()

        # Insert at end (most recent within freq=1)
        self.freq_table[frequency][key] = None

        # New keys always reset min frequency
        self.min_freq = frequency

    def on_update(self, cache: OrderedDict, key: str) -> None:
        self._touch(key=key)

    def on_access(self, cache: OrderedDict, key: str) -> None:
        self._touch(key=key)

    def on_delete(self, cache, key) -> None:
        freq = self.freq.pop(key)

        bucket = self.freq_table[freq]
        bucket.pop(key)

        # Clean up empty bucket
        if not bucket:
            del self.freq_table[freq]

            # Fix min_freq if needed
            if self.min_freq == freq:
                self.min_freq = min(self.freq_table.keys(), default=0)

    def select_eviction_key(self, cache: OrderedDict) -> str:
        if not cache:
            raise RuntimeError("Eviction requested on empty cache")

        bucket = self.freq_table[self.min_freq]

        return next(iter(bucket))

    def _touch(self, key: str) -> None:
        old_freq = self.freq[key]
        new_freq = old_freq + 1
        self.freq[key] = new_freq

        bucket = self.freq_table[old_freq]
        bucket.pop(key)

        if not bucket:
            del self.freq_table[old_freq]
            if self.min_freq == old_freq:
                self.min_freq = min(self.freq_table.keys(), default=new_freq)

        if new_freq not in self.freq_table:
            self.freq_table[new_freq] = OrderedDict()

        self.freq_table[new_freq][key] = None
