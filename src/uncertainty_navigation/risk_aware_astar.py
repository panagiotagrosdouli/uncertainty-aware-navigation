"""Risk-aware A* planner using uncertainty and occupancy probability costs."""

from __future__ import annotations

import numpy as np

from uncertainty_navigation.astar import Cell, astar
from uncertainty_navigation.planning import risk_weighted_cost


def risk_aware_astar(
    occupancy: np.ndarray,
    uncertainty: np.ndarray,
    start: Cell,
    goal: Cell,
    lambda_uncertainty: float,
    occupancy_probability: np.ndarray | None = None,
    mu_occupancy: float = 0.0,
) -> list[Cell] | None:
    """Run A* with risk-aware traversal costs.

    The risk cost can combine uncertainty and occupancy probability:

    ```text
    cost = distance + lambda * uncertainty + mu * P(occupied)
    ```
    """

    if occupancy.shape != uncertainty.shape:
        raise ValueError("occupancy and uncertainty maps must have the same shape")
    if occupancy_probability is not None and occupancy_probability.shape != occupancy.shape:
        raise ValueError("occupancy_probability must have the same shape as occupancy")

    def cost_fn(cell: Cell) -> float:
        probability = 0.0 if occupancy_probability is None else float(occupancy_probability[cell])
        return risk_weighted_cost(
            geometric_cost=0.0,
            uncertainty=float(uncertainty[cell]),
            lambda_uncertainty=lambda_uncertainty,
            occupancy_probability=probability,
            mu_occupancy=mu_occupancy,
        )

    return astar(occupancy=occupancy, start=start, goal=goal, cost_fn=cost_fn)
