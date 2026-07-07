"""Online uncertainty-aware navigation simulation loop."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from uncertainty_navigation.exploration import (
    ExplorationState,
    initialize_exploration,
    planning_map_from_exploration,
    update_exploration,
)
from uncertainty_navigation.replanning import advance_path, compute_replan, next_step_from_path
from uncertainty_navigation.robot import RobotState

Cell = tuple[int, int]


@dataclass(frozen=True)
class SimulationConfig:
    """Configuration for an online navigation rollout."""

    planner_name: str
    lambda_uncertainty: float
    sensor_radius: int
    max_steps: int = 500
    treat_unknown_as_free: bool = True


@dataclass
class SimulationResult:
    """Result of an online navigation rollout."""

    success: bool
    steps: int
    replans: int
    collisions: int
    final_coverage: float
    final_mean_uncertainty: float
    path_history: list[Cell] = field(default_factory=list)


def run_online_navigation(
    ground_truth_occupancy: np.ndarray,
    start: Cell,
    goal: Cell,
    config: SimulationConfig,
) -> SimulationResult:
    """Run observe-plan-move-replan navigation on a grid map."""

    robot = RobotState(position=start, goal=goal)
    exploration = initialize_exploration(ground_truth_occupancy.shape)
    current_path: list[Cell] | None = None
    collisions = 0

    while not robot.at_goal and robot.steps < config.max_steps:
        exploration = update_exploration(
            state=exploration,
            ground_truth_occupancy=ground_truth_occupancy,
            robot_position=robot.position,
            sensor_radius=config.sensor_radius,
        )
        planning_occupancy = planning_map_from_exploration(
            exploration,
            treat_unknown_as_free=config.treat_unknown_as_free,
        )

        plan = compute_replan(
            planner_name=config.planner_name,
            occupancy=planning_occupancy,
            uncertainty=exploration.uncertainty,
            start=robot.position,
            goal=goal,
            lambda_uncertainty=config.lambda_uncertainty,
        )
        robot.register_replan()
        current_path = plan.path

        next_cell = next_step_from_path(current_path)
        if next_cell is None:
            break

        if ground_truth_occupancy[next_cell] == 1:
            collisions += 1
            # Stop on collision in this first simulation version.
            break

        robot.move_to(next_cell)
        current_path = advance_path(current_path)

    exploration = update_exploration(
        state=exploration,
        ground_truth_occupancy=ground_truth_occupancy,
        robot_position=robot.position,
        sensor_radius=config.sensor_radius,
    )

    return SimulationResult(
        success=robot.at_goal,
        steps=robot.steps,
        replans=robot.replans,
        collisions=collisions,
        final_coverage=exploration.coverage,
        final_mean_uncertainty=exploration.mean_uncertainty,
        path_history=robot.path_history,
    )
