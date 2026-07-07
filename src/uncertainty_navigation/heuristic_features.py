"""Grid-node feature extraction for uncertainty-aware planning.

This module adapts the reusable feature idea from the DynNav uncertainty-A*
experiments, while keeping this repository independent from learned models.
The features can later support uncertainty estimation, learned heuristics, or
analysis of planner behaviour.
"""
from __future__ import annotations

import math

import numpy as np

Cell = tuple[int, int]


def extract_grid_features(cell: Cell, goal: Cell, occupancy: np.ndarray) -> np.ndarray:
    """Extract an 11-dimensional feature vector for a grid cell.

    Features
    --------
    0. signed row distance to goal
    1. signed column distance to goal
    2. Euclidean distance to goal
    3. Manhattan distance to goal
    4. Chebyshev distance to goal
    5. number of free four-connected neighbors
    6. number of blocked four-connected neighbors
    7. local obstacle density in a 3x3 window
    8. near-obstacle indicator
    9. normalized row coordinate
    10. normalized column coordinate
    """

    row, col = cell
    goal_row, goal_col = goal
    height, width = occupancy.shape

    d_row = goal_row - row
    d_col = goal_col - col
    euclidean = math.sqrt(d_row * d_row + d_col * d_col)
    manhattan = abs(d_row) + abs(d_col)
    chebyshev = max(abs(d_row), abs(d_col))

    neighbor_cells = [
        (row - 1, col),
        (row + 1, col),
        (row, col - 1),
        (row, col + 1),
    ]
    free_neighbors = sum(
        1
        for n_row, n_col in neighbor_cells
        if 0 <= n_row < height and 0 <= n_col < width and occupancy[n_row, n_col] == 0
    )
    blocked_neighbors = 4 - free_neighbors

    row_min, row_max = max(0, row - 1), min(height, row + 2)
    col_min, col_max = max(0, col - 1), min(width, col + 2)
    local_window = occupancy[row_min:row_max, col_min:col_max]
    local_obstacle_density = float(np.mean(local_window != 0)) if local_window.size else 0.0
    near_obstacle = 1.0 if local_obstacle_density > 0.0 else 0.0

    normalized_row = row / max(height - 1, 1)
    normalized_col = col / max(width - 1, 1)

    return np.array(
        [
            d_row,
            d_col,
            euclidean,
            manhattan,
            chebyshev,
            free_neighbors,
            blocked_neighbors,
            local_obstacle_density,
            near_obstacle,
            normalized_row,
            normalized_col,
        ],
        dtype=np.float32,
    )
