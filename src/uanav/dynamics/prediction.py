"""Transparent dynamic-obstacle prediction without learned trajectory claims."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class DynamicAgent:
    position: tuple[float, float]
    velocity: tuple[float, float]
    position_std: float = 0.5
    velocity_std: float = 0.1


def predict_dynamic_risk(
    shape: tuple[int, int],
    agents: list[DynamicAgent],
    horizon: int,
    safety_radius: float = 1.5,
) -> np.ndarray:
    """Return ``(horizon, rows, cols)`` collision-probability proxy layers."""
    if horizon <= 0:
        raise ValueError("horizon must be positive")
    rows, cols = np.indices(shape)
    layers = np.zeros((horizon, *shape), dtype=float)
    for step in range(horizon):
        time = float(step)
        for agent in agents:
            mean_row = agent.position[0] + agent.velocity[0] * time
            mean_col = agent.position[1] + agent.velocity[1] * time
            spread = max(1e-6, agent.position_std + time * agent.velocity_std)
            distance_squared = (rows - mean_row) ** 2 + (cols - mean_col) ** 2
            gaussian = np.exp(-0.5 * distance_squared / spread**2)
            proximity = np.exp(-np.sqrt(distance_squared) / max(safety_radius, 1e-6))
            agent_risk = np.clip(0.65 * gaussian + 0.35 * proximity, 0.0, 1.0)
            layers[step] = 1.0 - (1.0 - layers[step]) * (1.0 - agent_risk)
    return np.clip(layers, 0.0, 1.0)


def path_dynamic_risk(path: list[tuple[int, int]], layers: np.ndarray) -> dict[str, float]:
    """Summarize time-aligned dynamic risk for a candidate path."""
    if not path:
        return {"accumulated_risk": 0.0, "maximum_risk": 0.0, "blockage_probability": 0.0}
    values = [float(layers[min(step, len(layers) - 1), point[0], point[1]]) for step, point in enumerate(path)]
    return {
        "accumulated_risk": float(sum(values)),
        "maximum_risk": float(max(values)),
        "blockage_probability": float(1.0 - np.prod([1.0 - value for value in values])),
    }
