"""Synthetic map generation for reproducible uncertainty-aware navigation experiments."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from uncertainty_navigation.core import Cell, GridMap


@dataclass(frozen=True)
class ScenarioConfig:
    """Configuration for deterministic synthetic grid maps."""

    size: int = 32
    obstacle_density: float = 0.2
    uncertainty_noise: float = 0.25
    obstacle_threshold: float = 0.5


def make_synthetic_grid(seed: int, config: ScenarioConfig) -> tuple[GridMap, Cell, Cell]:
    """Create a deterministic synthetic grid with a safe corridor and uncertain shortcut.

    The generator intentionally creates two plausible route classes: a shorter central
    corridor with higher uncertainty and a longer border corridor with lower uncertainty.
    This makes the first experiment diagnostic rather than purely random.
    """

    rng = np.random.default_rng(seed)
    size = config.size
    if size < 8:
        raise ValueError("size must be at least 8 for the diagnostic scenario")

    occupancy = np.zeros((size, size), dtype=np.float64)
    uncertainty = rng.uniform(0.05, config.uncertainty_noise, size=(size, size))

    random_obstacles = rng.random((size, size)) < config.obstacle_density
    occupancy[random_obstacles] = 1.0

    # Clear deterministic border route.
    occupancy[1, 1 : size - 1] = 0.0
    occupancy[1 : size - 1, size - 2] = 0.0
    uncertainty[1, 1 : size - 1] = 0.05
    uncertainty[1 : size - 1, size - 2] = 0.05

    # Clear shorter central route but mark it uncertain.
    mid = size // 2
    occupancy[mid, 1 : size - 1] = 0.0
    occupancy[1:mid, 1] = 0.0
    occupancy[mid:size - 1, size - 2] = 0.0
    uncertainty[mid, 1 : size - 1] = 0.85
    uncertainty[1:mid, 1] = 0.75
    uncertainty[mid:size - 1, size - 2] = 0.75

    start = (1, 1)
    goal = (size - 2, size - 2)
    occupancy[start] = 0.0
    occupancy[goal] = 0.0
    uncertainty[start] = 0.0
    uncertainty[goal] = 0.0

    return GridMap(occupancy, uncertainty, config.obstacle_threshold), start, goal
