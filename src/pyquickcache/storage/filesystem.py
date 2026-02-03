from typing import Any
from .base import StorageBackend
from ._file_manager import FileManager  # or move file.py here
from ..exceptions import CacheSaveError, CacheLoadError
from ..serializer import BaseSerializer
from typing import Type, TYPE_CHECKING

if TYPE_CHECKING:
    from ..serializer import BaseSerializer


class FileSystemStorage(StorageBackend):
    """
    INTERNAL.

    Filesystem-based storage backend using FileManager.
    """

    def __init__(
        self,
        base_dir: str,
        default_filename: str,
        serializer: Type[BaseSerializer],
        filepath: str | None = None,
        use_timestamp: bool = False,
    ):
        self.file_manager = FileManager(
            default_dir=base_dir,
            default_filename=default_filename,
        )
        self.serializer = serializer
        self.filepath = filepath
        self.use_timestamp = use_timestamp

    def save(self, data: Any) -> None:
        try:
            path = self.file_manager.resolve_path(
                self.filepath,
                extension=self.serializer.extension,
                use_timestamp=self.use_timestamp,
            )
            serialized = self.serializer.serialize(data)
            self.file_manager.write(path, serialized)
        except Exception as e:
            raise CacheSaveError(self.filepath, e) from e

    def load(self) -> Any:
        try:
            path = self.file_manager.resolve_path(
                self.filepath,
                extension=self.serializer.extension,
                use_timestamp=False,
            )
            raw = self.file_manager.read(path, binary=self.serializer.is_binary)
            return self.serializer.deserialize(raw)
        except Exception as e:
            raise CacheLoadError(self.filepath, e) from e
