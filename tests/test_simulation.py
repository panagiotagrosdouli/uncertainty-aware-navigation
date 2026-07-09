import numpy as np

from uncertainty_navigation.simulation import ScenarioConfig, make_synthetic_grid


def test_synthetic_grid_is_deterministic() -> None:
    cfg = ScenarioConfig(size=16, obstacle_density=0.1)
    grid_a, start_a, goal_a = make_synthetic_grid(7, cfg)
    grid_b, start_b, goal_b = make_synthetic_grid(7, cfg)
    assert start_a == start_b
    assert goal_a == goal_b
    assert np.array_equal(grid_a.occupancy, grid_b.occupancy)
    assert np.array_equal(grid_a.uncertainty, grid_b.uncertainty)


def test_synthetic_grid_has_valid_start_and_goal() -> None:
    grid, start, goal = make_synthetic_grid(0, ScenarioConfig(size=16))
    assert not grid.is_blocked(start)
    assert not grid.is_blocked(goal)
    assert grid.uncertainty[start] == 0.0
    assert grid.uncertainty[goal] == 0.0
