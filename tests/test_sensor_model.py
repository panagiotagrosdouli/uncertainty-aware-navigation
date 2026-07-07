"""Tests for partial-observation sensor utilities."""
from __future__ import annotations

import numpy as np

from uncertainty_navigation.sensor_model import (
    UNKNOWN,
    circular_observation_mask,
    observe_occupancy,
    planning_occupancy_from_partial,
    uncertainty_from_observation,
)


def test_circular_observation_mask_includes_center() -> None:
    mask = circular_observation_mask(shape=(5, 5), position=(2, 2), radius=1)

    assert mask[2, 2]
    assert mask[0, 0] is np.False_ or not bool(mask[0, 0])


def test_observe_occupancy_marks_unseen_cells_unknown() -> None:
    ground_truth = np.zeros((5, 5), dtype=int)
    observed = observe_occupancy(ground_truth, position=(2, 2), radius=0)

    assert observed[2, 2] == 0
    assert observed[0, 0] == UNKNOWN


def test_uncertainty_from_observation_high_for_unknown_cells() -> None:
    observed = np.array([[0, UNKNOWN], [1, UNKNOWN]])
    uncertainty = uncertainty_from_observation(observed)

    assert uncertainty[0, 0] == 0.0
    assert uncertainty[0, 1] == 1.0
    assert uncertainty[1, 0] == 0.0
    assert uncertainty[1, 1] == 1.0


def test_planning_occupancy_can_treat_unknown_as_free() -> None:
    observed = np.array([[0, UNKNOWN], [1, UNKNOWN]])
    planning_map = planning_occupancy_from_partial(observed, treat_unknown_as_free=True)

    assert planning_map[0, 1] == 0
    assert planning_map[1, 1] == 0
