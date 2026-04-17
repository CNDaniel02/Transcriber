from __future__ import annotations

from pathlib import Path


class ProgressCallback:
    def on_info(self, message: str) -> None:
        return None

    def on_batch_start(self, total_files: int) -> None:
        return None

    def on_file_start(self, index: int, total: int, file_path: Path) -> None:
        return None

    def on_file_done(self, index: int, total: int, file_path: Path, output_path: Path) -> None:
        return None

    def on_error(self, index: int, total: int, file_path: Path, error: str) -> None:
        return None

    def on_complete(self, total: int, success: int, failed: int) -> None:
        return None


class NullProgressCallback(ProgressCallback):
    pass
