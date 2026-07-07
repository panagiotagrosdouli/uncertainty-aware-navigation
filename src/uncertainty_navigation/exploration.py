"""Exploration-state utilities for online map updates."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from uncertainty_navigation.bayes_update import (
    initialize_log_odds_grid,
    occupancy_probability_grid,
    planning_occupancy_from_probability,
    uncertainty_from_probability,
    update_log_odds_grid,
)
from uncertainty_navigation.sensor_model import UNKNOWN, observe_occupancy

Cell = tuple[int, int]


@dataclass
class ExplorationState:
    """Probabilistic partial map state maintained during exploration."""

    observed_occupancy: np.ndarray
    log_odds: np.ndarray
    occupancy_probability: np.ndarray
    uncertainty: np.ndarray

    @property
    def coverage(self) -> float:
        """Fraction of cells that are no longer unknown."""

        return float(np.mean(self.observed_occupancy != UNKNOWN))

    @property
    def mean_uncertainty(self) -> float:
        """Mean uncertainty over the whole map."""

        return float(np.mean(self.uncertainty))


def initialize_exploration(shape: tuple[int, int], prior: float = 0.5) -> ExplorationState:
    """Create a fully unknown probabilistic exploration state."""

    observed_occupancy = np.full(shape, fill_value=UNKNOWN, dtype=int)
    log_odds = initialize_log_odds_grid(shape, prior=prior)
    occupancy_probability = occupancy_probability_grid(log_odds)
    uncertainty = uncertainty_from_probability(occupancy_probability)
    return ExplorationState(
        observed_occupancy=observed_occupancy,
        log_odds=log_odds,
        occupancy_probability=occupancy_probability,
        uncertainty=uncertainty,
    )


def update_exploration(
    state: ExplorationState,
    ground_truth_occupancy: np.ndarray,
    robot_position: Cell,
    sensor_radius: int,
) -> ExplorationState:
    """Update the partial map using a new probabilistic sensor observation."""

    new_observation = observe_occupancy(
        ground_truth_occupancy=ground_truth_occupancy,
        position=robot_position,
        radius=sensor_radius,
    )
    observed_occupancy = state.observed_occupancy.copy()
    newly_seen = new_observation != UNKNOWN
    observed_occupancy[newly_seen] = new_observation[newly_seen]

    log_odds = update_log_odds_grid(state.log_odds, new_observation)
    occupancy_probability = occupancy_probability_grid(log_odds)
    uncertainty = uncertainty_from_probability(occupancy_probability)

    return ExplorationState(
        observed_occupancy=observed_occupancy,
        log_odds=log_odds,
        occupancy_probability=occupancy_probability,
        uncertainty=uncertainty,
    )


def planning_map_from_exploration(
    state: ExplorationState,
    treat_unknown_as_free: bool = True,
) -> np.ndarray:
    """Convert the exploration state into a planner-compatible occupancy grid."""

    planning_map = planning_occupancy_from_probability(state.occupancy_probability)
    if treat_unknown_as_free:
        planning_map[state.observed_occupancy == UNKNOWN] = 0
    return planning_map
