from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from uanav.simulation.dynamic_obstacles import DynamicObstacle


@dataclass(frozen=True)
class DynamicRiskResult:
    risk: float
    predicted_distance: float
    time_to_closest_approach: float
    closing_speed: float
    collision_predicted: bool
    near_miss_predicted: bool


def closest_approach(
    robot_position: np.ndarray,
    robot_velocity: np.ndarray,
    obstacle: DynamicObstacle,
    horizon_s: float,
) -> tuple[float, float, float]:
    robot_position = np.asarray(robot_position, dtype=float).reshape(2)
    robot_velocity = np.asarray(robot_velocity, dtype=float).reshape(2)
    relative_position = obstacle.position - robot_position
    relative_velocity = obstacle.velocity - robot_velocity
    speed_sq = float(relative_velocity @ relative_velocity)
    if speed_sq <= 1e-12:
        t_closest = 0.0
    else:
        t_closest = float(np.clip(-(relative_position @ relative_velocity) / speed_sq, 0.0, horizon_s))
    separation = relative_position + relative_velocity * t_closest
    distance = float(np.linalg.norm(separation))
    closing_speed = max(0.0, -float(relative_position @ relative_velocity) / max(np.linalg.norm(relative_position), 1e-9))
    return distance, t_closest, closing_speed


def dynamic_risk(
    robot_position: np.ndarray,
    robot_velocity: np.ndarray,
    obstacle: DynamicObstacle,
    horizon_s: float = 4.0,
    robot_radius: float = 0.4,
    near_miss_margin: float = 0.8,
) -> DynamicRiskResult:
    if horizon_s <= 0 or robot_radius <= 0 or near_miss_margin < 0:
        raise ValueError("invalid dynamic-risk parameters")
    distance, t_closest, closing_speed = closest_approach(
        robot_position=robot_position,
        robot_velocity=robot_velocity,
        obstacle=obstacle,
        horizon_s=horizon_s,
    )
    collision_distance = robot_radius + obstacle.radius
    near_miss_distance = collision_distance + near_miss_margin
    sigma = max(obstacle.process_noise_std * np.sqrt(max(t_closest, 1e-9)), 0.05)
    distance_risk = 1.0 / (1.0 + np.exp((distance - near_miss_distance) / sigma))
    temporal_risk = np.exp(-t_closest / max(horizon_s, 1e-9))
    velocity_risk = 1.0 - np.exp(-closing_speed)
    uncertainty_risk = 1.0 - np.exp(-sigma)
    score = float(np.clip(0.55 * distance_risk + 0.20 * temporal_risk + 0.15 * velocity_risk + 0.10 * uncertainty_risk, 0.0, 1.0))
    return DynamicRiskResult(
        risk=score,
        predicted_distance=distance,
        time_to_closest_approach=t_closest,
        closing_speed=closing_speed,
        collision_predicted=distance <= collision_distance,
        near_miss_predicted=distance <= near_miss_distance,
    )


def rasterize_dynamic_risk(
    shape: tuple[int, int],
    obstacles: list[DynamicObstacle],
    horizon_s: float = 4.0,
    dt: float = 0.5,
) -> np.ndarray:
    field = np.zeros(shape, dtype=float)
    rows, cols = np.indices(shape)
    for obstacle in obstacles:
        for time_s, mean, covariance in obstacle.predict(horizon_s=horizon_s, dt=dt):
            variance = max(float(np.trace(covariance) / 2.0), 0.04)
            distance_sq = (rows - mean[0]) ** 2 + (cols - mean[1]) ** 2
            occupancy = np.exp(-0.5 * distance_sq / variance)
            temporal_discount = np.exp(-time_s / max(horizon_s, 1e-9))
            field = np.maximum(field, occupancy * temporal_discount)
    return np.clip(field, 0.0, 1.0)
