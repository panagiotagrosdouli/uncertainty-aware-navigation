"""Planner interfaces used by the experiment scripts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np

from uncertainty_navigation.astar import astar
from uncertainty_navigation.risk_aware_astar import risk_aware_astar

Cell = tuple[int, int]
PlannerName = Literal["astar", "risk_aware_astar"]


@dataclass(frozen=True)
class PlannerResult:
    """Result returned by a planner call."""

    planner_name: str
    path: list[Cell] | None
    lambda_uncertainty: float | None = None


def plan_path(
    planner_name: PlannerName,
    occupancy: np.ndarray,
    uncertainty: np.ndarray,
    start: Cell,
    goal: Cell,
    lambda_uncertainty: float = 0.0,
) -> PlannerResult:
    """Run one of the supported planners."""

    if planner_name == "astar":
        return PlannerResult(planner_name="astar", path=astar(occupancy, start, goal))

    if planner_name == "risk_aware_astar":
        return PlannerResult(
            planner_name="risk_aware_astar",
            path=risk_aware_astar(occupancy, uncertainty, start, goal, lambda_uncertainty),
            lambda_uncertainty=lambda_uncertainty,
        )

    raise ValueError(f"Unsupported planner: {planner_name}")
