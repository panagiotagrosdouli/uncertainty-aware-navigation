from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class LocalizationState:
    estimated_pose: np.ndarray
    ground_truth_pose: np.ndarray
    covariance: np.ndarray

    def __post_init__(self) -> None:
        self.estimated_pose = np.asarray(self.estimated_pose, dtype=float).reshape(2)
        self.ground_truth_pose = np.asarray(self.ground_truth_pose, dtype=float).reshape(2)
        self.covariance = np.asarray(self.covariance, dtype=float).reshape(2, 2)
        validate_covariance(self.covariance)

    @property
    def error(self) -> float:
        return float(np.linalg.norm(self.estimated_pose - self.ground_truth_pose))

    @property
    def uncertainty(self) -> float:
        return float(np.sqrt(max(np.linalg.det(self.covariance), 0.0)))

    def predict(self, control: np.ndarray, dt: float, process_noise: np.ndarray) -> None:
        if dt <= 0:
            raise ValueError("dt must be positive")
        control = np.asarray(control, dtype=float).reshape(2)
        process_noise = np.asarray(process_noise, dtype=float).reshape(2, 2)
        validate_covariance(process_noise)
        self.estimated_pose = self.estimated_pose + control * dt
        self.ground_truth_pose = self.ground_truth_pose + control * dt
        self.covariance = self.covariance + process_noise * dt
        validate_covariance(self.covariance)

    def inject_drift(self, drift: np.ndarray) -> None:
        self.estimated_pose = self.estimated_pose + np.asarray(drift, dtype=float).reshape(2)

    def correct(self, observation: np.ndarray, observation_covariance: np.ndarray) -> None:
        observation = np.asarray(observation, dtype=float).reshape(2)
        observation_covariance = np.asarray(observation_covariance, dtype=float).reshape(2, 2)
        validate_covariance(observation_covariance)
        innovation_covariance = self.covariance + observation_covariance
        gain = self.covariance @ np.linalg.inv(innovation_covariance)
        self.estimated_pose = self.estimated_pose + gain @ (observation - self.estimated_pose)
        identity = np.eye(2)
        self.covariance = (identity - gain) @ self.covariance @ (identity - gain).T + gain @ observation_covariance @ gain.T
        self.covariance = 0.5 * (self.covariance + self.covariance.T)
        validate_covariance(self.covariance)


def validate_covariance(covariance: np.ndarray, tolerance: float = 1e-10) -> None:
    covariance = np.asarray(covariance, dtype=float)
    if covariance.shape != (2, 2):
        raise ValueError("covariance must have shape (2, 2)")
    if not np.all(np.isfinite(covariance)):
        raise ValueError("covariance must be finite")
    if not np.allclose(covariance, covariance.T, atol=tolerance):
        raise ValueError("covariance must be symmetric")
    if np.min(np.linalg.eigvalsh(covariance)) < -tolerance:
        raise ValueError("covariance must be positive semidefinite")


def covariance_ellipse(covariance: np.ndarray, confidence_scale: float = 2.0) -> tuple[float, float, float]:
    validate_covariance(covariance)
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    order = np.argsort(eigenvalues)[::-1]
    eigenvalues = eigenvalues[order]
    eigenvectors = eigenvectors[:, order]
    width, height = 2.0 * confidence_scale * np.sqrt(np.maximum(eigenvalues, 0.0))
    angle_deg = float(np.degrees(np.arctan2(eigenvectors[1, 0], eigenvectors[0, 0])))
    return float(width), float(height), angle_deg


def pose_uncertainty_risk(covariance: np.ndarray, reference_variance: float = 1.0) -> float:
    validate_covariance(covariance)
    if reference_variance <= 0:
        raise ValueError("reference_variance must be positive")
    trace = float(np.trace(covariance))
    return float(np.clip(1.0 - np.exp(-trace / reference_variance), 0.0, 1.0))
