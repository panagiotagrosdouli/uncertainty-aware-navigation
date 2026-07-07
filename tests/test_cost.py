"""Tests for risk-aware planning cost functions."""

from __future__ import annotations

import pytest

from uncertainty_navigation.planning import risk_weighted_cost, uncertainty_weighted_cost


def test_uncertainty_weighted_cost_adds_penalty() -> None:
    cost = uncertainty_weighted_cost(
        geometric_cost=1.0,
        uncertainty=0.5,
        lambda_uncertainty=2.0,
    )

    assert cost == 2.0


def test_uncertainty_weighted_cost_rejects_negative_lambda() -> None:
    with pytest.raises(ValueError):
        uncertainty_weighted_cost(
            geometric_cost=1.0,
            uncertainty=0.5,
            lambda_uncertainty=-1.0,
        )


def test_risk_weighted_cost_adds_occupancy_probability_penalty() -> None:
    cost = risk_weighted_cost(
        geometric_cost=1.0,
        uncertainty=0.5,
        lambda_uncertainty=2.0,
        occupancy_probability=0.25,
        mu_occupancy=4.0,
    )

    assert cost == 3.0


def test_risk_weighted_cost_rejects_negative_mu() -> None:
    with pytest.raises(ValueError):
        risk_weighted_cost(
            geometric_cost=1.0,
            uncertainty=0.5,
            lambda_uncertainty=1.0,
            occupancy_probability=0.5,
            mu_occupancy=-1.0,
        )
