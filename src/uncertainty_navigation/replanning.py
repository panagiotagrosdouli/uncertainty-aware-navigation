"""Replanning utilities for online uncertainty-aware navigation."""
from __future__ import annotations

from uncertainty_navigation.planner import PlannerResult, plan_path

Cell = tuple[int, int]


def should_replan(
    current_path: list[Cell] | None,
    robot_position: Cell,
    goal: Cell,
) -> bool:
    """Return whether a new path should be computed."""

    if robot_position == goal:
        return False
    if current_path is None or len(current_path) < 2:
        return True
    return current_path[0] != robot_position


def compute_replan(
    planner_name: str,
    occupancy,
    uncertainty,
    start: Cell,
    goal: Cell,
    lambda_uncertainty: float,
) -> PlannerResult:
    """Compute a new plan from the current robot position."""

    return plan_path(
        planner_name=planner_name,
        occupancy=occupancy,
        uncertainty=uncertainty,
        start=start,
        goal=goal,
        lambda_uncertainty=lambda_uncertainty,
    )


def next_step_from_path(path: list[Cell] | None) -> Cell | None:
    """Return the next executable step from a planned path."""

    if path is None or len(path) < 2:
        return None
    return path[1]


def advance_path(path: list[Cell] | None) -> list[Cell] | None:
    """Drop the already executed first cell from a path."""

    if path is None or len(path) <= 1:
        return None
    return path[1:]
