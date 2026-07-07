"""Risk-aware A* planner using map uncertainty as traversal cost."""

from __future__ import annotations

import numpy as np

from uncertainty_navigation.astar import Cell, astar
from uncertainty_navigation.planning import uncertainty_weighted_cost


def risk_aware_astar(
    occupancy: np.ndarray,
    uncertainty: np.ndarray,
    start: Cell,
    goal: Cell,
    lambda_uncertainty: float,
) -> list[Cell] | None:
    """Run A* with an uncertainty-weighted traversal cost."""

    if occupancy.shape != uncertainty.shape:
        raise ValueError("occupancy and uncertainty maps must have the same shape")

    def cost_fn(cell: Cell) -> float:
        return uncertainty_weighted_cost(
            geometric_cost=0.0,
            uncertainty=float(uncertainty[cell]),
            lambda_uncertainty=lambda_uncertainty,
        )

    return astar(occupancy=occupancy, start=start, goal=goal, cost_fn=cost_fn)
