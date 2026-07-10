"""Belief-state data models for the research prototype."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Observation:
    """One binary occupancy observation."""

    row: int
    col: int
    occupied: bool
    confidence: float
    timestamp: int
    range_m: float = 0.0
    source: str = "simulated_range_sensor"


@dataclass(frozen=True)
class BeliefCell:
    """Serializable per-cell belief summary."""

    occupancy_probability: float
    entropy: float
    observation_count: int
    last_observation_time: int | None
    confidence: float
    semantic_status: str = "unknown"

    def to_dict(self) -> dict:
        return asdict(self)
