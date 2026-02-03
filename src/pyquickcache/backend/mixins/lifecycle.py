from abc import ABC, abstractmethod


class LifecycleMixin(ABC):
    """
    Mixin for backend lifecycle management.

    Provides hooks for closing resources and handling other things on exit.
    """

    @abstractmethod
    def close(self) -> None:
        """
        Release backend resources and perform cleanup.

        For in-memory backend, this is a no-op. Other backends (files, network connections) may override.
        """
        pass
