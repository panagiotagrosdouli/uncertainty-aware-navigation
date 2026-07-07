"""Exploration-state utilities for online map updates."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from uncertainty_navigation.sensor_model import (
    UNKNOWN,
    observe_occupancy,
    planning_occupancy_from_partial,
    uncertainty_from_observation,
)

Cell = tuple[int, int]


@dataclass
class ExplorationState:
    """Partial map state maintained by the robot during exploration."""

    observed_occupancy: np.ndarray
    uncertainty: np.ndarray

    @property
    def coverage(self) -> float:
        """Fraction of cells that are no longer unknown."""

        return float(np.mean(self.observed_occupancy != UNKNOWN))

    @property
    def mean_uncertainty(self) -> float:
        """Mean uncertainty over the whole map."""

        return float(np.mean(self.uncertainty))


def initialize_exploration(shape: tuple[int, int]) -> ExplorationState:
    """Create a fully unknown exploration state."""

    observed_occupancy = np.full(shape, fill_value=UNKNOWN, dtype=int)
    uncertainty = uncertainty_from_observation(observed_occupancy)
    return ExplorationState(observed_occupancy=observed_occupancy, uncertainty=uncertainty)


def update_exploration(
    state: ExplorationState,
    ground_truth_occupancy: np.ndarray,
    robot_position: Cell,
    sensor_radius: int,
) -> ExplorationState:
    """Update the partial map using a new sensor observation."""

    new_observation = observe_occupancy(
        ground_truth_occupancy=ground_truth_occupancy,
        position=robot_position,
        radius=sensor_radius,
    )
    observed_occupancy = state.observed_occupancy.copy()
    newly_seen = new_observation != UNKNOWN
    observed_occupancy[newly_seen] = new_observation[newly_seen]
    uncertainty = uncertainty_from_observation(observed_occupancy)
    return ExplorationState(observed_occupancy=observed_occupancy, uncertainty=uncertainty)


def planning_map_from_exploration(
    state: ExplorationState,
    treat_unknown_as_free: bool = True,
) -> np.ndarray:
    """Convert the exploration state into a planner-compatible occupancy grid."""

    return planning_occupancy_from_partial(
        state.observed_occupancy,
        treat_unknown_as_free=treat_unknown_as_free,
    )
