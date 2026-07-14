from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from math import hypot
from pathlib import Path
from typing import Sequence
import json
import platform
import time

import numpy as np


@dataclass(frozen=True)
class Pose2D:
    x_m: float
    y_m: float
    yaw_rad: float
    frame_id: str = "map"
    timestamp_s: float = 0.0


@dataclass(frozen=True)
class DynamicObstacle:
    obstacle_id: str
    pose: Pose2D
    velocity_mps: tuple[float, float]
    covariance_m2: tuple[tuple[float, float], tuple[float, float]] = ((0.04, 0.0), (0.0, 0.04))


@dataclass(frozen=True)
class PredictedObstacleState:
    obstacle_id: str
    timestamp_s: float
    x_m: float
    y_m: float
    covariance_trace_m2: float


@dataclass(frozen=True)
class CandidatePath:
    candidate_id: str
    points_m: tuple[tuple[float, float], ...]
    progress_cost: float
    uncertainty_exposure: float
    static_risk: float
    recoverability: float
    information_gain: float = 0.0


@dataclass(frozen=True)
class RiskEstimate:
    expected: float
    cvar: float
    worst_case: float
    collision_proxy: float
    calibrated_upper_bound: float
    sample_count: int


class SupervisorState(StrEnum):
    NORMAL = "NORMAL"
    CAUTION = "CAUTION"
    SLOW_DOWN = "SLOW_DOWN"
    REPLAN = "REPLAN"
    ACTIVE_PERCEPTION = "ACTIVE_PERCEPTION"
    RECOVERY = "RECOVERY"
    SAFE_STOP = "SAFE_STOP"
    EMERGENCY_STOP = "EMERGENCY_STOP"
    MISSION_ABORT = "MISSION_ABORT"


@dataclass(frozen=True)
class SafetyDecision:
    state: SupervisorState
    allow_motion: bool
    speed_scale: float
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class ConformalResult:
    target_coverage: float
    quantile: float
    empirical_coverage: float
    mean_interval_width: float
    coverage_violation: float


def cvar(values: Sequence[float], alpha: float = 0.9) -> float:
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must lie in (0, 1)")
    if not values:
        raise ValueError("values must not be empty")
    ordered = np.sort(np.asarray(values, dtype=float))
    start = min(len(ordered) - 1, int(np.floor(alpha * len(ordered))))
    return float(np.mean(ordered[start:]))


def split_conformal_absolute(
    calibration_errors: Sequence[float], test_errors: Sequence[float], target_coverage: float = 0.9
) -> ConformalResult:
    if not 0.0 < target_coverage < 1.0:
        raise ValueError("target_coverage must lie in (0, 1)")
    cal = np.abs(np.asarray(calibration_errors, dtype=float))
    test = np.abs(np.asarray(test_errors, dtype=float))
    if cal.size == 0 or test.size == 0:
        raise ValueError("calibration and test errors must be non-empty")
    rank = int(np.ceil((cal.size + 1) * target_coverage))
    rank = min(max(rank, 1), cal.size)
    q = float(np.partition(cal, rank - 1)[rank - 1])
    coverage = float(np.mean(test <= q))
    return ConformalResult(
        target_coverage=target_coverage,
        quantile=q,
        empirical_coverage=coverage,
        mean_interval_width=2.0 * q,
        coverage_violation=max(0.0, target_coverage - coverage),
    )


def predict_constant_velocity(
    obstacle: DynamicObstacle, horizon_s: float, step_s: float, covariance_growth_m2_s: float = 0.03
) -> tuple[PredictedObstacleState, ...]:
    if horizon_s <= 0 or step_s <= 0:
        raise ValueError("horizon_s and step_s must be positive")
    vx, vy = obstacle.velocity_mps
    initial_trace = obstacle.covariance_m2[0][0] + obstacle.covariance_m2[1][1]
    states = []
    for t in np.arange(step_s, horizon_s + 1e-12, step_s):
        states.append(
            PredictedObstacleState(
                obstacle_id=obstacle.obstacle_id,
                timestamp_s=obstacle.pose.timestamp_s + float(t),
                x_m=obstacle.pose.x_m + vx * float(t),
                y_m=obstacle.pose.y_m + vy * float(t),
                covariance_trace_m2=initial_trace + 2.0 * covariance_growth_m2_s * float(t),
            )
        )
    return tuple(states)


def dynamic_interaction_samples(
    path: CandidatePath, prediction: Sequence[PredictedObstacleState], robot_radius_m: float = 0.25
) -> list[float]:
    if not path.points_m or not prediction:
        return [0.0]
    samples: list[float] = []
    for idx, state in enumerate(prediction):
        point = path.points_m[min(idx, len(path.points_m) - 1)]
        clearance = hypot(point[0] - state.x_m, point[1] - state.y_m) - robot_radius_m
        sigma = max(0.05, np.sqrt(state.covariance_trace_m2))
        samples.append(float(np.exp(-max(clearance, 0.0) / sigma)))
    return samples


def adaptive_sample_count(risk_margin: float, prediction_modes: int, localization_trace: float, shifted: bool) -> int:
    count = 32
    if risk_margin < 0.15:
        count += 64
    if prediction_modes > 1:
        count += 32 * (prediction_modes - 1)
    if localization_trace > 0.25:
        count += 64
    if shifted:
        count += 64
    return min(count, 256)


def estimate_risk(samples: Sequence[float], conformal_margin: float, alpha: float = 0.9) -> RiskEstimate:
    arr = np.clip(np.asarray(samples, dtype=float), 0.0, 1.0)
    expected = float(np.mean(arr))
    tail = cvar(arr.tolist(), alpha)
    upper = min(1.0, tail + max(0.0, conformal_margin))
    return RiskEstimate(expected, tail, float(np.max(arr)), expected, upper, len(arr))


def viability_score(path: CandidatePath, min_clearance_m: float, escape_routes: int, safe_stop_available: bool) -> float:
    clearance_term = min(1.0, max(0.0, min_clearance_m / 0.8))
    escape_term = min(1.0, escape_routes / 2.0)
    stop_term = 1.0 if safe_stop_available else 0.0
    return 0.4 * clearance_term + 0.35 * escape_term + 0.25 * stop_term


def shield(
    risk: RiskEstimate,
    localization_trace: float,
    sensor_age_s: float,
    viable: bool,
    emergency_stop_available: bool,
    max_risk: float = 0.45,
) -> SafetyDecision:
    reasons: list[str] = []
    if not emergency_stop_available:
        return SafetyDecision(SupervisorState.MISSION_ABORT, False, 0.0, ("emergency stop unavailable",))
    if sensor_age_s > 1.0:
        return SafetyDecision(SupervisorState.SAFE_STOP, False, 0.0, (f"sensor age {sensor_age_s:.2f}s exceeds 1.00s",))
    if not viable:
        return SafetyDecision(SupervisorState.RECOVERY, False, 0.0, ("no admissible fallback trajectory",))
    if risk.calibrated_upper_bound > max_risk:
        reasons.append(f"calibrated risk bound {risk.calibrated_upper_bound:.3f} exceeds {max_risk:.3f}")
        return SafetyDecision(SupervisorState.REPLAN, False, 0.0, tuple(reasons))
    if localization_trace > 0.5:
        return SafetyDecision(SupervisorState.SLOW_DOWN, True, 0.25, ("localization covariance is high",))
    if risk.calibrated_upper_bound > 0.3:
        return SafetyDecision(SupervisorState.CAUTION, True, 0.5, ("risk bound is near threshold",))
    return SafetyDecision(SupervisorState.NORMAL, True, 1.0, ())


def score_path(path: CandidatePath, risk: RiskEstimate, viability: float) -> float:
    return (
        path.progress_cost
        + 2.0 * path.uncertainty_exposure
        + 3.0 * path.static_risk
        + 4.0 * risk.cvar
        + 5.0 * risk.calibrated_upper_bound
        - 2.0 * viability
        - 1.5 * path.information_gain
    )


def run_research_smoke(output_dir: str | Path = "results") -> dict:
    started = time.perf_counter()
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    calibration = split_conformal_absolute(
        [0.03, 0.06, 0.04, 0.08, 0.12, 0.05, 0.09, 0.07, 0.11],
        [0.02, 0.05, 0.10, 0.13, 0.08],
        0.9,
    )
    obstacle = DynamicObstacle("crossing-1", Pose2D(2.0, -0.5, 0.0), (0.0, 0.6))
    prediction = predict_constant_velocity(obstacle, 4.0, 0.5)
    direct = CandidatePath("direct", tuple((0.5 * i, 0.0) for i in range(9)), 4.0, 0.2, 0.1, 0.25)
    fallback = CandidatePath("fallback", tuple((0.5 * i, 2.5) for i in range(10)), 4.8, 0.12, 0.08, 0.8)
    records = []
    for path, clearance, routes in ((direct, 0.18, 0), (fallback, 0.7, 2)):
        samples = dynamic_interaction_samples(path, prediction)
        sample_count = adaptive_sample_count(0.1 if path.candidate_id == "direct" else 0.4, 2, 0.3, False)
        expanded = (samples * ((sample_count + len(samples) - 1) // len(samples)))[:sample_count]
        risk = estimate_risk(expanded, calibration.quantile)
        viability = viability_score(path, clearance, routes, routes > 0)
        decision = shield(risk, 0.3, 0.1, viability >= 0.5, True)
        records.append(
            {
                "candidate_id": path.candidate_id,
                "score": score_path(path, risk, viability),
                "risk": asdict(risk),
                "viability": viability,
                "safety": {**asdict(decision), "state": str(decision.state)},
            }
        )
    admissible = [r for r in records if r["safety"]["allow_motion"]]
    selected = min(admissible, key=lambda r: r["score"]) if admissible else None
    payload = {
        "status": "Synthetic Validation",
        "selected_candidate": selected["candidate_id"] if selected else None,
        "candidates": records,
        "calibration": asdict(calibration),
        "runtime_s": time.perf_counter() - started,
        "environment": {"python": platform.python_version(), "platform": platform.platform()},
    }
    (output / "research_smoke.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload
