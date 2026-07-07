"""Planning abstractions for uncertainty-aware navigation.

This module will contain baseline and risk-aware planners. The first planned
implementation is a grid-based A* planner with an optional uncertainty penalty.
"""

from __future__ import annotations


def uncertainty_weighted_cost(geometric_cost: float, uncertainty: float, lambda_uncertainty: float) -> float:
    """Compute a simple uncertainty-weighted traversal cost.

    Parameters
    ----------
    geometric_cost:
        The standard traversal cost of a cell or edge.
    uncertainty:
        Estimated environmental uncertainty for the cell or edge.
    lambda_uncertainty:
        Weight controlling how strongly uncertainty affects planning.

    Returns
    -------
    float
        Combined traversal cost.
    """

    if lambda_uncertainty < 0:
        raise ValueError("lambda_uncertainty must be non-negative")

    return geometric_cost + lambda_uncertainty * uncertainty
