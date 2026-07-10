"""Transparent simulated range sensor with FOV, occlusion, noise, delay, and dropout."""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

from uanav.belief.models import Observation


@dataclass(frozen=True)
class SensorConfig:
    radius: float = 6.0
    field_of_view_deg: float = 120.0
    false_positive_rate: float = 0.03
    false_negative_rate: float = 0.08
    range_noise_scale: float = 0.25
    dropout_probability: float = 0.0
    delay_steps: int = 0
    seed: int = 7


def _angle_delta(a: float, b: float) -> float:
    return abs((a - b + math.pi) % (2 * math.pi) - math.pi)


def _line_cells(start: tuple[int, int], end: tuple[int, int]) -> list[tuple[int, int]]:
    r0, c0 = start
    r1, c1 = end
    steps = max(abs(r1 - r0), abs(c1 - c0))
    if steps == 0:
        return [start]
    cells = []
    for i in range(steps + 1):
        t = i / steps
        cells.append((round(r0 + t * (r1 - r0)), round(c0 + t * (c1 - c0))))
    return list(dict.fromkeys(cells))


class RangeSensor:
    def __init__(self, config: SensorConfig = SensorConfig()) -> None:
        self.config = config
        self.rng = np.random.default_rng(config.seed)
        self._pending: list[tuple[int, Observation]] = []

    def visible_cells(
        self,
        ground_truth: np.ndarray,
        position: tuple[int, int],
        heading_rad: float,
    ) -> list[tuple[int, int, float]]:
        visible: list[tuple[int, int, float]] = []
        fov = math.radians(self.config.field_of_view_deg) / 2
        for row in range(ground_truth.shape[0]):
            for col in range(ground_truth.shape[1]):
                dr, dc = row - position[0], col - position[1]
                distance = math.hypot(dr, dc)
                if distance > self.config.radius:
                    continue
                bearing = math.atan2(dr, dc)
                if distance > 0 and _angle_delta(bearing, heading_rad) > fov:
                    continue
                ray = _line_cells(position, (row, col))
                if any(ground_truth[cell] == 1 for cell in ray[1:-1]):
                    continue
                visible.append((row, col, distance))
        return visible

    def observe(
        self,
        ground_truth: np.ndarray,
        position: tuple[int, int],
        heading_rad: float,
        timestamp: int,
    ) -> list[Observation]:
        ready = [obs for release, obs in self._pending if release <= timestamp]
        self._pending = [(release, obs) for release, obs in self._pending if release > timestamp]
        if self.rng.random() < self.config.dropout_probability:
            return ready
        for row, col, distance in self.visible_cells(ground_truth, position, heading_rad):
            occupied = bool(ground_truth[row, col])
            error = self.config.false_negative_rate if occupied else self.config.false_positive_rate
            range_fraction = min(1.0, distance / max(self.config.radius, 1e-9))
            effective_error = min(0.49, error + self.config.range_noise_scale * range_fraction * 0.1)
            measured = not occupied if self.rng.random() < effective_error else occupied
            directional = max(0.55, 1.0 - effective_error)
            obs = Observation(row, col, measured, directional, timestamp, distance)
            release = timestamp + self.config.delay_steps
            if release <= timestamp:
                ready.append(obs)
            else:
                self._pending.append((release, obs))
        return ready
