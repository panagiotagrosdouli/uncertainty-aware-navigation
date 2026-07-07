"""Tests for risk-aware planning cost functions."""

from __future__ import annotations

import pytest

from uncertainty_navigation.planning import uncertainty_weighted_cost


def test_uncertainty_weighted_cost_adds_penalty() -> None:
    assert uncertainty_weighted_cost(geometric_cost=1.0, uncertainty=0.5, lambda_uncertainty=2.0) == 2.0


def test_uncertainty_weighted_cost_rejects_negative_lambda() -> None:
    with pytest.raises(ValueError):
        uncertainty_weighted_cost(geometric_cost=1.0, uncertainty=0.5, lambda_uncertainty=-1.0)
