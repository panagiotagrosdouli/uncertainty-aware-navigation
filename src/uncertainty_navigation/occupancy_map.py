"""Occupancy-map utilities."""

from __future__ import annotations

import numpy as np


FREE = 0
OBSTACLE = 1


def is_free(occupancy: np.ndarray, cell: tuple[int, int]) -> bool:
    """Return whether a cell is traversable."""

    row, col = cell
    return bool(occupancy[row, col] == FREE)


def in_bounds(occupancy: np.ndarray, cell: tuple[int, int]) -> bool:
    """Return whether a cell lies inside the grid."""

    row, col = cell
    return 0 <= row < occupancy.shape[0] and 0 <= col < occupancy.shape[1]


def obstacle_density(occupancy: np.ndarray) -> float:
    """Compute the fraction of occupied cells."""

    return float(np.mean(occupancy == OBSTACLE))
