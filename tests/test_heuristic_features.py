"""Tests for grid-node feature extraction."""
from __future__ import annotations

import numpy as np

from uncertainty_navigation.heuristic_features import extract_grid_features


def test_extract_grid_features_has_expected_shape() -> None:
    occupancy = np.zeros((5, 5), dtype=int)
    features = extract_grid_features(cell=(0, 0), goal=(4, 4), occupancy=occupancy)

    assert features.shape == (11,)


def test_extract_grid_features_detects_near_obstacle() -> None:
    occupancy = np.zeros((5, 5), dtype=int)
    occupancy[1, 1] = 1

    features = extract_grid_features(cell=(1, 2), goal=(4, 4), occupancy=occupancy)

    near_obstacle = features[8]
    assert near_obstacle == 1.0
