"""Evaluation metrics for uncertainty-aware navigation paths."""

from __future__ import annotations

import math
from collections.abc import Iterable

import numpy as np

from uncertainty_navigation.core import Cell, GridMap, PlanResult, TrialMetrics


def evaluate_path(seed: int, grid: GridMap, result: PlanResult) -> TrialMetrics:
    """Convert a planner result into reproducible scalar metrics."""

    path = result.path
    collision = any(grid.occupancy[cell] >= grid.obstacle_threshold for cell in path)
    accumulated_uncertainty = float(sum(grid.uncertainty[cell] for cell in path))
    accumulated_occupancy = float(sum(grid.occupancy[cell] for cell in path))
    min_distance = min_obstacle_distance(grid, path) if path else 0.0
    return TrialMetrics(
        seed=seed,
        planner=result.planner,
        success=result.success,
        collision=collision,
        path_length=result.path_length,
        accumulated_uncertainty=accumulated_uncertainty,
        accumulated_occupancy=accumulated_occupancy,
        min_obstacle_distance=min_distance,
        expanded_nodes=result.expanded_nodes,
        runtime_s=result.runtime_s,
        cost=result.cost,
    )


def min_obstacle_distance(grid: GridMap, path: Iterable[Cell]) -> float:
    """Return the minimum Euclidean distance from path cells to occupied cells."""

    path_cells = list(path)
    obstacles = np.argwhere(grid.occupancy >= grid.obstacle_threshold)
    if not path_cells or obstacles.size == 0:
        return math.inf
    min_distance = math.inf
    for row, col in path_cells:
        distances = np.sqrt((obstacles[:, 0] - row) ** 2 + (obstacles[:, 1] - col) ** 2)
        min_distance = min(min_distance, float(distances.min()))
    return min_distance
