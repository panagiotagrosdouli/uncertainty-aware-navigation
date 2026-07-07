"""Tests for Bayesian occupancy-grid updates."""
from __future__ import annotations

import numpy as np

from uncertainty_navigation.bayes_update import (
    FREE,
    OBSTACLE,
    UNKNOWN,
    initialize_log_odds_grid,
    occupancy_probability_grid,
    planning_occupancy_from_probability,
    uncertainty_from_probability,
    update_log_odds_grid,
)


def test_initialize_log_odds_grid_has_prior_probability() -> None:
    log_odds = initialize_log_odds_grid((3, 3), prior=0.5)
    probability = occupancy_probability_grid(log_odds)

    assert np.allclose(probability, 0.5)


def test_update_log_odds_increases_obstacle_probability() -> None:
    log_odds = initialize_log_odds_grid((2, 2), prior=0.5)
    observation = np.array([[OBSTACLE, UNKNOWN], [UNKNOWN, UNKNOWN]])

    updated = update_log_odds_grid(log_odds, observation)
    probability = occupancy_probability_grid(updated)

    assert probability[0, 0] > 0.5
    assert probability[0, 1] == 0.5


def test_update_log_odds_decreases_free_probability() -> None:
    log_odds = initialize_log_odds_grid((2, 2), prior=0.5)
    observation = np.array([[FREE, UNKNOWN], [UNKNOWN, UNKNOWN]])

    updated = update_log_odds_grid(log_odds, observation)
    probability = occupancy_probability_grid(updated)

    assert probability[0, 0] < 0.5
    assert probability[0, 1] == 0.5


def test_uncertainty_from_probability_is_maximal_at_half() -> None:
    probabilities = np.array([0.0, 0.5, 1.0])
    uncertainty = uncertainty_from_probability(probabilities)

    assert uncertainty[1] == 1.0
    assert uncertainty[0] == 0.0
    assert uncertainty[2] == 0.0


def test_planning_occupancy_from_probability_thresholds_obstacles() -> None:
    probabilities = np.array([[0.2, 0.8]])
    planning_map = planning_occupancy_from_probability(probabilities, occupancy_threshold=0.65)

    assert planning_map[0, 0] == 0
    assert planning_map[0, 1] == 1
