"""Bayesian occupancy-grid update utilities.

The implementation uses the standard log-odds representation for occupancy
probabilities. A prior probability of 0.5 corresponds to zero log-odds and
maximal uncertainty.
"""
from __future__ import annotations

import numpy as np

FREE = 0
OBSTACLE = 1
UNKNOWN = -1


def probability_to_log_odds(probability: float | np.ndarray) -> float | np.ndarray:
    """Convert occupancy probability to log-odds."""

    clipped = np.clip(probability, 1e-6, 1.0 - 1e-6)
    return np.log(clipped / (1.0 - clipped))


def log_odds_to_probability(log_odds: float | np.ndarray) -> float | np.ndarray:
    """Convert log-odds values to occupancy probabilities."""

    return 1.0 / (1.0 + np.exp(-log_odds))


def initialize_log_odds_grid(shape: tuple[int, int], prior: float = 0.5) -> np.ndarray:
    """Create a log-odds grid initialized with a prior occupancy probability."""

    return np.full(shape, fill_value=probability_to_log_odds(prior), dtype=float)


def update_log_odds_grid(
    log_odds_grid: np.ndarray,
    observation: np.ndarray,
    occupied_update: float = 0.85,
    free_update: float = 0.30,
    unknown_value: int = UNKNOWN,
    clamp_min: float = -5.0,
    clamp_max: float = 5.0,
) -> np.ndarray:
    """Apply an inverse-sensor-model update to a log-odds grid.

    Parameters
    ----------
    log_odds_grid:
        Current log-odds occupancy grid.
    observation:
        Partial observation using 0 for free, 1 for occupied, and -1 for unknown.
    occupied_update:
        Probability assigned when the sensor observes an occupied cell.
    free_update:
        Probability assigned when the sensor observes a free cell.
    unknown_value:
        Value used for unobserved cells.
    clamp_min, clamp_max:
        Numerical bounds for accumulated log-odds values.
    """

    updated = log_odds_grid.copy()
    occupied_mask = observation == OBSTACLE
    free_mask = observation == FREE

    updated[occupied_mask] += probability_to_log_odds(occupied_update)
    updated[free_mask] += probability_to_log_odds(free_update)
    updated[observation == unknown_value] += 0.0

    return np.clip(updated, clamp_min, clamp_max)


def occupancy_probability_grid(log_odds_grid: np.ndarray) -> np.ndarray:
    """Return occupancy probabilities from a log-odds grid."""

    return log_odds_to_probability(log_odds_grid).astype(float)


def uncertainty_from_probability(probability_grid: np.ndarray) -> np.ndarray:
    """Compute normalized uncertainty from occupancy probabilities.

    The expression 4p(1-p) is maximal at p=0.5 and minimal near p=0 or p=1.
    """

    return 4.0 * probability_grid * (1.0 - probability_grid)


def planning_occupancy_from_probability(
    probability_grid: np.ndarray,
    occupancy_threshold: float = 0.65,
) -> np.ndarray:
    """Convert occupancy probabilities into a binary planner occupancy grid."""

    return (probability_grid >= occupancy_threshold).astype(int)
