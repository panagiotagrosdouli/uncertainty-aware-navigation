"""Predict uncertainty evolution along candidate paths.

Research Prototype: this is a transparent analytical approximation, not a learned
state estimator or exact belief-space optimizer.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

Point = tuple[int, int]


@dataclass(frozen=True)
class PredictiveUncertainty:
    accumulated_occupancy_uncertainty: float
    localization_covariance: tuple[float, ...]
    observation_opportunities: int
    expected_information_gain: float
    maximum_uncertainty: float
    critical_passage_uncertainty: float
    terminal_uncertainty: float
    post_observation_uncertainty: tuple[float, ...]


def predict_path_uncertainty(
    path: list[Point],
    entropy: np.ndarray,
    observation_mask: np.ndarray | None = None,
    initial_localization_variance: float = 0.05,
    process_variance: float = 0.02,
    observation_reduction: float = 0.45,
) -> PredictiveUncertainty:
    """Predict occupancy and localization uncertainty along ``path``.

    Expected observations reduce local entropy and localization variance by a
    fixed documented fraction. Cells outside ``observation_mask`` only accrue
    process variance.
    """
    if not path:
        return PredictiveUncertainty(0.0, (), 0, 0.0, 0.0, 0.0, 0.0, ())

    mask = np.zeros_like(entropy, dtype=bool) if observation_mask is None else observation_mask.astype(bool)
    covariance = float(initial_localization_variance)
    covariance_history: list[float] = []
    post_observation: list[float] = []
    information_gain = 0.0
    opportunities = 0
    current_values: list[float] = []

    for point in path:
        value = float(entropy[point])
        current_values.append(value)
        covariance += process_variance
        if mask[point]:
            reduced = value * (1.0 - observation_reduction)
            information_gain += value - reduced
            value = reduced
            covariance *= 1.0 - observation_reduction
            opportunities += 1
        post_observation.append(value)
        covariance_history.append(covariance)

    critical = max(current_values) if current_values else 0.0
    return PredictiveUncertainty(
        accumulated_occupancy_uncertainty=float(sum(post_observation)),
        localization_covariance=tuple(covariance_history),
        observation_opportunities=opportunities,
        expected_information_gain=float(information_gain),
        maximum_uncertainty=float(max(current_values)),
        critical_passage_uncertainty=float(critical),
        terminal_uncertainty=float(post_observation[-1]),
        post_observation_uncertainty=tuple(post_observation),
    )
