from dataclasses import dataclass
from typing import Any, Optional


@dataclass(slots=True)
class CacheResponse:
    success: bool
    message: str
    data: Optional[Any] = None
