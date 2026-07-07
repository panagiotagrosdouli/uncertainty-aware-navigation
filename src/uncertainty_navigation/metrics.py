"""Evaluation metrics for navigation experiments."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

Cell = tuple[int, int]


@dataclass(frozen=True)
class PathMetrics:
    """Summary metrics for a planned path."""

    success: bool
    path_length: int
    accumulated_risk_cost: float
    collision_count: int


def path_length(path: list[Cell] | None) -> int:
    """Return the number of transitions in a path."""

    if path is None:
        return 0
    return max(len(path) - 1, 0)


def collision_count(path: list[Cell] | None, occupancy: np.ndarray) -> int:
    """Count occupied cells traversed by a path."""

    if path is None:
        return 0
    return int(sum(occupancy[cell] == 1 for cell in path))


def accumulated_risk_cost(path: list[Cell] | None, uncertainty: np.ndarray) -> float:
    """Compute accumulated uncertainty along a path."""

    if path is None:
        return float("inf")
    return float(sum(uncertainty[cell] for cell in path))


def evaluate_path(
    path: list[Cell] | None,
    occupancy: np.ndarray,
    uncertainty: np.ndarray,
) -> PathMetrics:
    """Evaluate a path using first-stage safety and efficiency metrics."""

    return PathMetrics(
        success=path is not None,
        path_length=path_length(path),
        accumulated_risk_cost=accumulated_risk_cost(path, uncertainty),
        collision_count=collision_count(path, occupancy),
    )
