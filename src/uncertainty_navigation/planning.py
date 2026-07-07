"""Planning cost functions for uncertainty-aware navigation."""

from __future__ import annotations


def uncertainty_weighted_cost(
    geometric_cost: float,
    uncertainty: float,
    lambda_uncertainty: float,
) -> float:
    """Compute a simple uncertainty-weighted traversal cost."""

    return risk_weighted_cost(
        geometric_cost=geometric_cost,
        uncertainty=uncertainty,
        lambda_uncertainty=lambda_uncertainty,
        occupancy_probability=0.0,
        mu_occupancy=0.0,
    )


def risk_weighted_cost(
    geometric_cost: float,
    uncertainty: float,
    lambda_uncertainty: float,
    occupancy_probability: float = 0.0,
    mu_occupancy: float = 0.0,
) -> float:
    """Compute traversal cost using uncertainty and occupancy probability.

    The cost follows the form:

    ```text
    cost = geometric_cost + lambda * uncertainty + mu * P(occupied)
    ```

    This allows risk-aware planning to penalize both epistemic uncertainty and
    estimated occupancy risk.
    """

    if lambda_uncertainty < 0:
        raise ValueError("lambda_uncertainty must be non-negative")
    if mu_occupancy < 0:
        raise ValueError("mu_occupancy must be non-negative")

    return geometric_cost + lambda_uncertainty * uncertainty + mu_occupancy * occupancy_probability
