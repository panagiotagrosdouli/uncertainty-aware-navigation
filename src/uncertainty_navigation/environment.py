"""Grid-map environment generation for navigation experiments."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class GridEnvironment:
    """A controlled two-dimensional grid environment.

    Parameters
    ----------
    occupancy:
        Binary occupancy grid where 1 denotes obstacle and 0 denotes free space.
    uncertainty:
        Continuous uncertainty grid with values in [0, 1].
    start:
        Start cell as ``(row, col)``.
    goal:
        Goal cell as ``(row, col)``.
    """

    occupancy: np.ndarray
    uncertainty: np.ndarray
    start: tuple[int, int]
    goal: tuple[int, int]

    def validate(self) -> None:
        """Validate environment dimensions and start-goal feasibility."""

        if self.occupancy.shape != self.uncertainty.shape:
            raise ValueError("occupancy and uncertainty maps must have the same shape")

        for name, cell in {"start": self.start, "goal": self.goal}.items():
            row, col = cell
            if not (0 <= row < self.occupancy.shape[0] and 0 <= col < self.occupancy.shape[1]):
                raise ValueError(f"{name} cell is outside the map")
            if self.occupancy[row, col] == 1:
                raise ValueError(f"{name} cell must be in free space")


def generate_random_grid(
    width: int,
    height: int,
    obstacle_density: float,
    uncertainty_level: float,
    seed: int | None = None,
) -> GridEnvironment:
    """Generate a random grid environment for controlled experiments."""

    if not 0 <= obstacle_density < 1:
        raise ValueError("obstacle_density must be in [0, 1)")
    if not 0 <= uncertainty_level <= 1:
        raise ValueError("uncertainty_level must be in [0, 1]")

    rng = np.random.default_rng(seed)
    occupancy = (rng.random((height, width)) < obstacle_density).astype(int)
    uncertainty = rng.random((height, width)) * uncertainty_level

    start = (0, 0)
    goal = (height - 1, width - 1)
    occupancy[start] = 0
    occupancy[goal] = 0

    environment = GridEnvironment(
        occupancy=occupancy,
        uncertainty=uncertainty,
        start=start,
        goal=goal,
    )
    environment.validate()
    return environment
