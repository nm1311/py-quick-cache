import os
import sys
from datetime import datetime
from typing import Optional, Union


class FileManager:

    def __init__(self, default_dir: str, default_filename: str):
        """
        Initialize with specific defaults for the intended use case.
        Example: FileManager("logs", "app_log")
        """
        self.default_dir = default_dir
        self.default_filename = default_filename

    def _get_project_root(self) -> str:
        """Locates the directory of the script that started the program."""
        try:
            main_module = sys.modules.get("__main__")
            if main_module and hasattr(main_module, "__file__"):
                return os.path.dirname(os.path.abspath(main_module.__file__))
        except Exception:
            pass
        return os.getcwd()

    def resolve_path(
        self, user_input: Optional[str], extension: str, use_timestamp: bool = False
    ) -> str:
        """
        Calculates the final file path based on user input and defaults.
        """
        project_root = self._get_project_root()
        storage_dir = os.path.join(project_root, self.default_dir)

        # 1. Handle Filename and Directory
        if not user_input:
            # Case: Nothing given -> Use the instance defaults
            base_name = self.default_filename
            target_dir = storage_dir

        elif os.path.isdir(user_input):
            # Case: Only a directory path was given
            base_name = self.default_filename
            target_dir = user_input

        else:
            # Case: Specific filename or Path+Filename given
            target_dir = os.path.dirname(user_input) or storage_dir
            base_name = os.path.basename(user_input)
            base_name = os.path.splitext(base_name)[0]

        # 2. Add Timestamp if requested
        if use_timestamp:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_name = f"{base_name}_{ts}_srr"  # Added the suffix for consistency

        # 3. Force the correct extension
        final_filename = f"{base_name}.{extension}"

        # 4. Ensure the directory exists
        os.makedirs(target_dir, exist_ok=True)

        return os.path.join(target_dir, final_filename)

    def write(self, path: str, data: Union[str, bytes], append: bool = False):
        """
        Writes data to disk. Automatically detects binary vs text mode.
        """
        # Determine base mode (write or append)
        base_mode = "a" if append else "w"

        # Determine if binary flag 'b' is needed based on data type
        mode = base_mode if isinstance(data, str) else f"{base_mode}b"

        with open(path, mode) as f:
            f.write(data)

    def read(self, path: str, binary: bool = False) -> Union[str, bytes]:
        """
        Reads data from disk.
        Use binary=True for Pickle files and binary=False for JSON/Logs.
        """
        if not os.path.exists(path):
            raise FileNotFoundError(f"No such file: {path}")

        mode = "rb" if binary else "r"

        with open(path, mode) as f:
            return f.read()
