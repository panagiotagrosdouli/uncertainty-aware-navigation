"""General utility functions for reproducible experiments."""

from __future__ import annotations

from pathlib import Path


def ensure_directory(path: str | Path) -> Path:
    """Create a directory if it does not already exist and return it as a Path."""

    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory
