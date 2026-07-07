"""Uncertainty-map utilities."""

from __future__ import annotations

import numpy as np


def validate_uncertainty_map(uncertainty: np.ndarray) -> None:
    """Validate that uncertainty values lie in [0, 1]."""

    if np.any(uncertainty < 0) or np.any(uncertainty > 1):
        raise ValueError("uncertainty values must lie in [0, 1]")


def accumulated_uncertainty(path: list[tuple[int, int]], uncertainty: np.ndarray) -> float:
    """Compute accumulated uncertainty along a path."""

    return float(sum(uncertainty[cell] for cell in path))


def normalize_uncertainty(values: np.ndarray) -> np.ndarray:
    """Normalize arbitrary uncertainty scores to [0, 1]."""

    min_value = float(np.min(values))
    max_value = float(np.max(values))
    if max_value == min_value:
        return np.zeros_like(values, dtype=float)
    return (values - min_value) / (max_value - min_value)
