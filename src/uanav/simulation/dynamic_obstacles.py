from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable

import numpy as np

PointF = tuple[float, float]


class MotionModel(str, Enum):
    CONSTANT_VELOCITY = "constant_velocity"
    WAYPOINT = "waypoint"
    RANDOM_WALK = "random_walk"
    CROSSING = "crossing"
    TEMPORARY_BLOCKAGE = "temporary_blockage"


@dataclass
class DynamicObstacle:
    obstacle_id: str
    position: np.ndarray
    velocity: np.ndarray
    radius: float = 0.45
    model: MotionModel = MotionModel.CONSTANT_VELOCITY
    waypoints: list[np.ndarray] = field(default_factory=list)
    waypoint_index: int = 0
    process_noise_std: float = 0.0
    active_from: float = 0.0
    active_until: float = float("inf")

    def __post_init__(self) -> None:
        self.position = np.asarray(self.position, dtype=float).reshape(2)
        self.velocity = np.asarray(self.velocity, dtype=float).reshape(2)
        self.waypoints = [np.asarray(p, dtype=float).reshape(2) for p in self.waypoints]
        if self.radius <= 0:
            raise ValueError("radius must be positive")
        if self.process_noise_std < 0:
            raise ValueError("process_noise_std must be non-negative")

    def is_active(self, time_s: float) -> bool:
        return self.active_from <= time_s <= self.active_until

    def update(self, dt: float, bounds: tuple[int, int], rng: np.random.Generator, time_s: float) -> None:
        if dt <= 0:
            raise ValueError("dt must be positive")
        if not self.is_active(time_s):
            return

        if self.model == MotionModel.WAYPOINT and self.waypoints:
            target = self.waypoints[self.waypoint_index]
            delta = target - self.position
            distance = float(np.linalg.norm(delta))
            if distance < max(0.15, float(np.linalg.norm(self.velocity)) * dt):
                self.position = target.copy()
                self.waypoint_index = (self.waypoint_index + 1) % len(self.waypoints)
            elif distance > 0:
                speed = max(float(np.linalg.norm(self.velocity)), 1e-6)
                self.velocity = speed * delta / distance
        elif self.model == MotionModel.RANDOM_WALK:
            self.velocity += rng.normal(0.0, self.process_noise_std, size=2)
        elif self.model == MotionModel.CROSSING:
            pass
        elif self.model == MotionModel.TEMPORARY_BLOCKAGE:
            self.velocity[:] = 0.0

        if self.process_noise_std > 0 and self.model != MotionModel.RANDOM_WALK:
            self.velocity += rng.normal(0.0, self.process_noise_std * np.sqrt(dt), size=2)

        self.position += self.velocity * dt
        height, width = bounds
        limits = np.array([height - 1.001, width - 1.001])
        lower = np.array([0.001, 0.001])
        for axis in (0, 1):
            if self.position[axis] < lower[axis] or self.position[axis] > limits[axis]:
                self.velocity[axis] *= -1
                self.position[axis] = np.clip(self.position[axis], lower[axis], limits[axis])

    def predict(self, horizon_s: float, dt: float) -> list[tuple[float, np.ndarray, np.ndarray]]:
        if horizon_s < 0 or dt <= 0:
            raise ValueError("horizon_s must be non-negative and dt must be positive")
        predictions: list[tuple[float, np.ndarray, np.ndarray]] = []
        steps = int(np.ceil(horizon_s / dt))
        for index in range(steps + 1):
            t = min(index * dt, horizon_s)
            mean = self.position + self.velocity * t
            variance = (self.process_noise_std**2) * max(t, 1e-9)
            covariance = np.eye(2) * variance
            predictions.append((t, mean, covariance))
        return predictions


@dataclass
class DynamicObstacleField:
    obstacles: list[DynamicObstacle]
    seed: int = 0
    time_s: float = 0.0

    def __post_init__(self) -> None:
        self._rng = np.random.default_rng(self.seed)

    def update(self, dt: float, bounds: tuple[int, int]) -> None:
        self.time_s += dt
        for obstacle in self.obstacles:
            obstacle.update(dt=dt, bounds=bounds, rng=self._rng, time_s=self.time_s)

    def active(self) -> Iterable[DynamicObstacle]:
        return (obstacle for obstacle in self.obstacles if obstacle.is_active(self.time_s))

    def snapshot(self) -> list[dict[str, object]]:
        return [
            {
                "obstacle_id": obstacle.obstacle_id,
                "position": obstacle.position.tolist(),
                "velocity": obstacle.velocity.tolist(),
                "radius": obstacle.radius,
                "model": obstacle.model.value,
                "active": obstacle.is_active(self.time_s),
            }
            for obstacle in self.obstacles
        ]
