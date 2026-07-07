"""Sensor and partial-observation utilities for grid-map experiments."""
from __future__ import annotations

import numpy as np

Cell = tuple[int, int]

UNKNOWN = -1
FREE = 0
OBSTACLE = 1


def circular_observation_mask(
    shape: tuple[int, int],
    position: Cell,
    radius: int,
) -> np.ndarray:
    """Return a boolean mask of cells visible inside a circular sensing radius."""

    if radius < 0:
        raise ValueError("radius must be non-negative")

    height, width = shape
    row, col = position
    rows, cols = np.ogrid[:height, :width]
    squared_distance = (rows - row) ** 2 + (cols - col) ** 2
    return squared_distance <= radius**2


def observe_occupancy(
    ground_truth_occupancy: np.ndarray,
    position: Cell,
    radius: int,
    unknown_value: int = UNKNOWN,
) -> np.ndarray:
    """Create a partially observed occupancy map from a sensing position."""

    observed = np.full_like(ground_truth_occupancy, fill_value=unknown_value)
    mask = circular_observation_mask(ground_truth_occupancy.shape, position, radius)
    observed[mask] = ground_truth_occupancy[mask]
    return observed


def uncertainty_from_observation(
    observed_occupancy: np.ndarray,
    unknown_value: int = UNKNOWN,
    known_uncertainty: float = 0.0,
    unknown_uncertainty: float = 1.0,
) -> np.ndarray:
    """Convert a partial occupancy map into an uncertainty layer."""

    uncertainty = np.full(observed_occupancy.shape, unknown_uncertainty, dtype=float)
    uncertainty[observed_occupancy != unknown_value] = known_uncertainty
    return uncertainty


def planning_occupancy_from_partial(
    observed_occupancy: np.ndarray,
    unknown_value: int = UNKNOWN,
    treat_unknown_as_free: bool = True,
) -> np.ndarray:
    """Convert partial observations into an occupancy map usable by planners.

    If unknown cells are treated as free, the risk-aware planner can still route
    through them but will pay the uncertainty penalty. If they are treated as
    occupied, planners become conservative and may fail when the goal is outside
    the observed region.
    """

    planning_map = observed_occupancy.copy()
    unknown_replacement = FREE if treat_unknown_as_free else OBSTACLE
    planning_map[planning_map == unknown_value] = unknown_replacement
    return planning_map.astype(int)
