import numpy as np
import pytest

from uanav.risk.dynamic_risk import dynamic_risk, rasterize_dynamic_risk
from uanav.simulation.dynamic_obstacles import DynamicObstacle, DynamicObstacleField, MotionModel
from uanav.uncertainty.localization import (
    LocalizationState,
    covariance_ellipse,
    pose_uncertainty_risk,
    validate_covariance,
)


def test_dynamic_obstacle_update_is_reproducible() -> None:
    def make_field() -> DynamicObstacleField:
        obstacle = DynamicObstacle(
            obstacle_id="rw",
            position=np.array([2.0, 2.0]),
            velocity=np.array([0.3, 0.1]),
            model=MotionModel.RANDOM_WALK,
            process_noise_std=0.05,
        )
        return DynamicObstacleField([obstacle], seed=11)

    first = make_field()
    second = make_field()
    for _ in range(5):
        first.update(0.2, (10, 10))
        second.update(0.2, (10, 10))
    assert np.allclose(first.obstacles[0].position, second.obstacles[0].position)
    assert np.allclose(first.obstacles[0].velocity, second.obstacles[0].velocity)


def test_collision_prediction_for_crossing_agent() -> None:
    obstacle = DynamicObstacle(
        obstacle_id="crossing",
        position=np.array([0.0, 2.0]),
        velocity=np.array([0.0, -1.0]),
        radius=0.4,
        model=MotionModel.CROSSING,
    )
    result = dynamic_risk(
        robot_position=np.array([0.0, 0.0]),
        robot_velocity=np.array([0.0, 1.0]),
        obstacle=obstacle,
        horizon_s=2.0,
        robot_radius=0.4,
    )
    assert result.collision_predicted
    assert result.near_miss_predicted
    assert result.predicted_distance == pytest.approx(0.0)
    assert 0.0 <= result.risk <= 1.0


def test_dynamic_risk_map_is_normalized() -> None:
    obstacle = DynamicObstacle("cv", np.array([3.0, 3.0]), np.array([0.0, 0.5]))
    field = rasterize_dynamic_risk((12, 12), [obstacle], horizon_s=2.0, dt=0.25)
    assert field.shape == (12, 12)
    assert np.isfinite(field).all()
    assert field.min() >= 0.0
    assert field.max() <= 1.0


def test_localization_covariance_prediction_and_correction() -> None:
    state = LocalizationState(
        estimated_pose=np.array([0.0, 0.0]),
        ground_truth_pose=np.array([0.0, 0.0]),
        covariance=np.eye(2) * 0.2,
    )
    original_trace = np.trace(state.covariance)
    state.predict(np.array([1.0, 0.0]), dt=1.0, process_noise=np.eye(2) * 0.1)
    predicted_trace = np.trace(state.covariance)
    assert predicted_trace > original_trace
    state.correct(np.array([1.0, 0.0]), observation_covariance=np.eye(2) * 0.05)
    assert np.trace(state.covariance) < predicted_trace
    validate_covariance(state.covariance)


def test_covariance_validation_rejects_non_psd_matrix() -> None:
    with pytest.raises(ValueError, match="positive semidefinite"):
        validate_covariance(np.array([[1.0, 2.0], [2.0, 1.0]]))


def test_covariance_ellipse_and_risk_are_finite() -> None:
    covariance = np.array([[0.4, 0.1], [0.1, 0.2]])
    width, height, angle = covariance_ellipse(covariance)
    assert width >= height >= 0.0
    assert np.isfinite(angle)
    assert 0.0 <= pose_uncertainty_risk(covariance) <= 1.0
