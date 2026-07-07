"""Tests for grid-based A* planning."""

from __future__ import annotations

import numpy as np

from uncertainty_navigation.astar import astar
from uncertainty_navigation.risk_aware_astar import risk_aware_astar


def test_astar_finds_path_on_empty_grid() -> None:
    occupancy = np.zeros((3, 3), dtype=int)
    path = astar(occupancy, start=(0, 0), goal=(2, 2))

    assert path is not None
    assert path[0] == (0, 0)
    assert path[-1] == (2, 2)


def test_astar_returns_none_when_goal_blocked() -> None:
    occupancy = np.zeros((3, 3), dtype=int)
    occupancy[2, 2] = 1

    path = astar(occupancy, start=(0, 0), goal=(2, 2))

    assert path is None


def test_risk_aware_astar_avoids_high_uncertainty_when_possible() -> None:
    occupancy = np.zeros((3, 4), dtype=int)
    uncertainty = np.zeros((3, 4), dtype=float)
    uncertainty[0, 1] = 1.0
    uncertainty[0, 2] = 1.0

    path = risk_aware_astar(
        occupancy=occupancy,
        uncertainty=uncertainty,
        start=(0, 0),
        goal=(0, 3),
        lambda_uncertainty=10.0,
    )

    assert path is not None
    assert (0, 1) not in path
    assert (0, 2) not in path
