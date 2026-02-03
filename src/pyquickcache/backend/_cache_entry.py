from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from ..utils.helpers import utcnow


@dataclass(slots=True)
class CacheEntry:
    """
    INTERNAL.

    Represents a single cache entry with an absolute expiration time.

    Purpose:
        Encapsulates the cached value along with TTL metadata and a computed
        expiration timestamp.

    Invariants:
        - expiration_time is always timezone-aware (UTC)
        - ttl is the original TTL (in seconds) used to compute expiration_time

    Notes:
        This class is not part of the public API and may change without notice.
    """

    value: Any
    expiration_time: datetime
    ttl: int

    def to_dict(self) -> dict:
        """
        INTERNAL.

        Serialize this cache entry into a dictionary representation.

        Purpose:
            Used by serializers and persistence layers to convert cache entries
            into a JSON-compatible format.

        Behavior:
            - Converts expiration_time to ISO 8601 string
            - Does not perform deep serialization of the value
        """

        return {
            "value": self.value,
            "expiration_time": self.expiration_time.isoformat(),  # Handle datetime conversion here
            "ttl": self.ttl,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CacheEntry":
        """
        INTERNAL.

        Serialize this cache entry into a dictionary representation.

        Purpose:
            Used by serializers and persistence layers to convert cache entries
            into a JSON-compatible format.

        Behavior:
            - Converts expiration_time to ISO 8601 string
            - Does not perform deep serialization of the value
        """

        expiration = datetime.fromisoformat(data["expiration_time"])

        # Ensure timezone awareness as fromisoformat may return naive datetime
        if expiration.tzinfo is None:
            expiration = expiration.replace(tzinfo=timezone.utc)

        return cls(
            value=data["value"],
            expiration_time=expiration,  # Revert string to datetime
            ttl=data["ttl"],
        )

    def is_expired(self) -> bool:
        """
        INTERNAL.

        Check whether this cache entry has expired.

        Behavior:
            - Compares the current UTC time against expiration_time
            - Does not mutate cache state

        Returns:
            bool: True if the entry is expired, False otherwise.
        """

        return utcnow() > self.expiration_time
