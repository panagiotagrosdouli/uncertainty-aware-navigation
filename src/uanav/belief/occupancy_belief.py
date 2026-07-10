"""Log-odds occupancy belief map with deterministic Bayesian updates."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .models import BeliefCell, Observation


def _logit(probability: np.ndarray | float) -> np.ndarray:
    p = np.clip(probability, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def _sigmoid(value: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-value))


def binary_entropy(probability: np.ndarray) -> np.ndarray:
    p = np.clip(probability, 1e-12, 1 - 1e-12)
    return -(p * np.log2(p) + (1 - p) * np.log2(1 - p))


class OccupancyBelief:
    """Grid belief represented in log-odds form."""

    def __init__(self, shape: tuple[int, int], prior: float = 0.5) -> None:
        if not 0 < prior < 1:
            raise ValueError("prior must be in (0, 1)")
        self.shape = shape
        self.prior = float(prior)
        self.log_odds = np.full(shape, float(_logit(prior)), dtype=float)
        self.observation_count = np.zeros(shape, dtype=int)
        self.last_observation_time = np.full(shape, -1, dtype=int)
        self.semantic_status = np.full(shape, "unknown", dtype=object)
        self.history: list[dict] = []

    @property
    def probability(self) -> np.ndarray:
        return _sigmoid(self.log_odds)

    @property
    def entropy(self) -> np.ndarray:
        return binary_entropy(self.probability)

    @property
    def confidence(self) -> np.ndarray:
        return 1.0 - self.entropy

    @property
    def unknown(self) -> np.ndarray:
        return self.observation_count == 0

    def update(self, observations: list[Observation]) -> list[dict]:
        events: list[dict] = []
        prior_log_odds = float(_logit(self.prior))
        for obs in observations:
            if not (0 <= obs.row < self.shape[0] and 0 <= obs.col < self.shape[1]):
                raise IndexError("observation outside belief map")
            confidence = float(np.clip(obs.confidence, 0.500001, 0.999999))
            inverse_probability = confidence if obs.occupied else 1.0 - confidence
            delta = float(_logit(inverse_probability)) - prior_log_odds
            before = float(self.probability[obs.row, obs.col])
            self.log_odds[obs.row, obs.col] = np.clip(
                self.log_odds[obs.row, obs.col] + delta,
                _logit(0.01),
                _logit(0.99),
            )
            self.observation_count[obs.row, obs.col] += 1
            self.last_observation_time[obs.row, obs.col] = obs.timestamp
            after = float(self.probability[obs.row, obs.col])
            self.semantic_status[obs.row, obs.col] = "occupied" if after >= 0.65 else "free" if after <= 0.35 else "uncertain"
            event = {
                "row": obs.row,
                "col": obs.col,
                "timestamp": obs.timestamp,
                "probability_before": before,
                "probability_after": after,
                "occupied_observation": obs.occupied,
                "confidence": confidence,
            }
            events.append(event)
            self.history.append(event)
        return events

    def cell(self, row: int, col: int) -> BeliefCell:
        probability = float(self.probability[row, col])
        timestamp = int(self.last_observation_time[row, col])
        return BeliefCell(
            occupancy_probability=probability,
            entropy=float(self.entropy[row, col]),
            observation_count=int(self.observation_count[row, col]),
            last_observation_time=None if timestamp < 0 else timestamp,
            confidence=float(self.confidence[row, col]),
            semantic_status=str(self.semantic_status[row, col]),
        )

    def assert_consistent(self) -> None:
        probability = self.probability
        if probability.shape != self.shape or not np.isfinite(probability).all():
            raise ValueError("invalid belief probability grid")
        if np.any((probability < 0) | (probability > 1)):
            raise ValueError("belief probability outside [0, 1]")
        if np.any(self.observation_count < 0):
            raise ValueError("negative observation count")

    def save(self, path: str | Path) -> None:
        payload = {
            "shape": list(self.shape),
            "prior": self.prior,
            "log_odds": self.log_odds.tolist(),
            "observation_count": self.observation_count.tolist(),
            "last_observation_time": self.last_observation_time.tolist(),
            "semantic_status": self.semantic_status.tolist(),
            "history": self.history,
        }
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "OccupancyBelief":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        belief = cls(tuple(payload["shape"]), payload["prior"])
        belief.log_odds = np.asarray(payload["log_odds"], dtype=float)
        belief.observation_count = np.asarray(payload["observation_count"], dtype=int)
        belief.last_observation_time = np.asarray(payload["last_observation_time"], dtype=int)
        belief.semantic_status = np.asarray(payload["semantic_status"], dtype=object)
        belief.history = list(payload.get("history", []))
        belief.assert_consistent()
        return belief
