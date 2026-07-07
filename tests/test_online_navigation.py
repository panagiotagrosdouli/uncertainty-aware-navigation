"""Tests for online navigation building blocks."""
from __future__ import annotations

import numpy as np

from uncertainty_navigation.exploration import initialize_exploration, update_exploration
from uncertainty_navigation.robot import RobotState
from uncertainty_navigation.simulation import SimulationConfig, run_online_navigation


def test_robot_state_tracks_motion_and_replans() -> None:
    robot = RobotState(position=(0, 0), goal=(0, 2))

    robot.register_replan()
    robot.move_to((0, 1))

    assert robot.steps == 1
    assert robot.replans == 1
    assert robot.path_history == [(0, 0), (0, 1)]
    assert not robot.at_goal


def test_exploration_update_increases_coverage() -> None:
    ground_truth = np.zeros((5, 5), dtype=int)
    state = initialize_exploration(ground_truth.shape)

    updated = update_exploration(
        state=state,
        ground_truth_occupancy=ground_truth,
        robot_position=(2, 2),
        sensor_radius=1,
    )

    assert updated.coverage > state.coverage
    assert updated.mean_uncertainty < state.mean_uncertainty


def test_online_navigation_reaches_goal_on_empty_grid() -> None:
    ground_truth = np.zeros((5, 5), dtype=int)
    config = SimulationConfig(
        planner_name="risk_aware_astar",
        lambda_uncertainty=1.0,
        sensor_radius=2,
        max_steps=20,
    )

    result = run_online_navigation(
        ground_truth_occupancy=ground_truth,
        start=(0, 0),
        goal=(4, 4),
        config=config,
    )

    assert result.success
    assert result.steps > 0
    assert result.replans > 0
    assert result.collisions == 0
