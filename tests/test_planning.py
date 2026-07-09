import numpy as np

from uncertainty_navigation.core import GridMap
from uncertainty_navigation.planning import GridPlanner


def test_astar_finds_path_on_empty_grid() -> None:
    grid = GridMap(np.zeros((5, 5)), np.zeros((5, 5)))
    result = GridPlanner().plan(grid, (0, 0), (4, 4))
    assert result.success
    assert result.path[0] == (0, 0)
    assert result.path[-1] == (4, 4)
    assert result.path_length == 9


def test_blocked_goal_returns_failure() -> None:
    occupancy = np.zeros((5, 5))
    occupancy[4, 4] = 1.0
    grid = GridMap(occupancy, np.zeros((5, 5)))
    result = GridPlanner().plan(grid, (0, 0), (4, 4))
    assert not result.success
    assert result.reason == "goal_blocked"


def test_uncertainty_penalty_changes_controlled_route() -> None:
    occupancy = np.ones((5, 7))
    uncertainty = np.zeros((5, 7))
    # Top corridor is shorter but uncertain.
    occupancy[1, 1:6] = 0.0
    uncertainty[1, 1:6] = 1.0
    # Bottom corridor is longer but certain.
    occupancy[3, 1:6] = 0.0
    occupancy[1:4, 1] = 0.0
    occupancy[1:4, 5] = 0.0
    uncertainty[3, 1:6] = 0.0
    uncertainty[1:4, 1] = 0.0
    uncertainty[1:4, 5] = 0.0
    grid = GridMap(occupancy, uncertainty)

    shortest = GridPlanner(name="shortest").plan(grid, (1, 1), (1, 5))
    cautious = GridPlanner(name="cautious", lambda_uncertainty=10.0).plan(grid, (1, 1), (1, 5))

    assert shortest.success
    assert cautious.success
    assert shortest.path_length < cautious.path_length
    assert sum(grid.uncertainty[cell] for cell in cautious.path) < sum(
        grid.uncertainty[cell] for cell in shortest.path
    )
