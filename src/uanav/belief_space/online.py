"""Deterministic online partial-observability integration scenario.

Synthetic Demo and Research Prototype: this connects belief updates, sensing,
active perception, predictive uncertainty, recoverability, and safety rejection.
It is not an exact POMDP solver.
"""

from __future__ import annotations

import csv
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from uanav.active_perception.planner import ActionType, PerceptionCandidate
from uanav.belief.occupancy_belief import OccupancyBelief
from uanav.explainability.decision import (
    CandidateDecisionInput,
    CandidateDecisionRecord,
    evaluate_candidate,
    select_admissible_candidate,
)
from uanav.safety.constraints import SafetyThresholds
from uanav.sensing.range_sensor import RangeSensor, SensorConfig
from uanav.uncertainty.predictive import predict_path_uncertainty

Point = tuple[int, int]


@dataclass(frozen=True)
class BeliefSpaceRun:
    selected_actions: tuple[str, ...]
    success: bool
    trajectory: tuple[Point, ...]
    observation_count: int
    map_update_count: int
    safety_rejection_count: int
    initial_mean_entropy: float
    final_mean_entropy: float
    information_gained: float
    decision_records: tuple[dict, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def _scenario() -> tuple[np.ndarray, Point, Point, Point, list[Point], list[Point], list[Point]]:
    ground_truth = np.zeros((9, 13), dtype=int)
    ground_truth[0, :] = 1
    ground_truth[-1, :] = 1
    ground_truth[:, 0] = 1
    ground_truth[:, -1] = 1
    ground_truth[4, 6] = 1
    start = (4, 1)
    goal = (4, 11)
    viewpoint = (2, 5)
    direct = [(4, col) for col in range(1, 12)]
    to_viewpoint = [(4, 1), (3, 1), (2, 1), (2, 2), (2, 3), (2, 4), viewpoint]
    alternate = [
        viewpoint,
        (3, 5),
        (4, 5),
        (5, 5),
        (6, 5),
        (6, 6),
        (6, 7),
        (6, 8),
        (6, 9),
        (5, 9),
        (4, 9),
        (4, 10),
        goal,
    ]
    return ground_truth, start, goal, viewpoint, direct, to_viewpoint, alternate


def _candidate_record(
    candidate: PerceptionCandidate,
    path: list[Point],
    belief: OccupancyBelief,
    safe_regions: set[Point],
    timestep: int,
) -> CandidateDecisionRecord:
    prediction = predict_path_uncertainty(path, belief.entropy)
    occupied_probability = max(float(belief.probability[point]) for point in path)
    minimum_clearance = 0.5 if occupied_probability >= 0.65 else 2.0
    decision = CandidateDecisionInput(
        candidate=candidate,
        path=path,
        collision_probability=occupied_probability,
        map_uncertainty=prediction.maximum_uncertainty,
        localization_uncertainty=max(prediction.localization_covariance, default=0.0),
        minimum_clearance=minimum_clearance,
        timestep=timestep,
    )
    return evaluate_candidate(
        decision,
        belief.probability,
        belief.entropy,
        safe_regions,
        safety_thresholds=SafetyThresholds(max_map_uncertainty=1.0),
        recoverability_threshold=0.35,
    )


def _write_rows(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run_belief_space_demo(output_dir: str | Path = "results") -> BeliefSpaceRun:
    ground_truth, start, goal, viewpoint, direct, to_viewpoint, alternate = _scenario()
    belief = OccupancyBelief(ground_truth.shape, prior=0.5)
    sensor = RangeSensor(
        SensorConfig(
            radius=5.0,
            field_of_view_deg=110.0,
            false_positive_rate=0.0,
            false_negative_rate=0.0,
            range_noise_scale=0.0,
            seed=7,
        )
    )
    initial_entropy = float(np.mean(belief.entropy))
    safe_regions = {start, viewpoint}
    trajectory = [start]
    selected_actions: list[str] = []
    decisions: list[CandidateDecisionRecord] = []
    observation_rows: list[dict] = []
    update_rows: list[dict] = []

    direct_candidate = PerceptionCandidate("direct", ActionType.MOVE_TOWARD_GOAL, 0.0, 10.0, 0.4, 0.2, 0.0)
    view_candidate = PerceptionCandidate("viewpoint", ActionType.MOVE_TO_VIEWPOINT, 2.0, 6.0, 0.05, 0.9, 2.0)
    initial_records = [
        _candidate_record(direct_candidate, direct, belief, safe_regions, 0),
        _candidate_record(view_candidate, to_viewpoint, belief, safe_regions, 0),
    ]
    decisions.extend(initial_records)
    selected = select_admissible_candidate(initial_records)
    if selected is None:
        selected_actions.append(ActionType.STOP)
    else:
        selected_actions.append(selected.selected_action)
        trajectory.extend(to_viewpoint[1:])

    heading = math.atan2(4 - viewpoint[0], 6 - viewpoint[1])
    observations = sensor.observe(ground_truth, viewpoint, heading, timestamp=1)
    for observation in observations:
        observation_rows.append(asdict(observation))
    update_rows.extend(belief.update(observations))

    direct_after = _candidate_record(direct_candidate, direct[4:], belief, safe_regions, 1)
    alternate_candidate = PerceptionCandidate("alternate", ActionType.REPLAN, 0.3, 13.0, 0.05, 0.8, 3.0)
    alternate_after = _candidate_record(alternate_candidate, alternate, belief, safe_regions, 1)
    decisions.extend([direct_after, alternate_after])
    selected = select_admissible_candidate([direct_after, alternate_after])
    if selected is None:
        selected_actions.append(ActionType.STOP)
    else:
        selected_actions.append(selected.selected_action)
        trajectory.extend(alternate[1:])

    result = BeliefSpaceRun(
        selected_actions=tuple(str(action) for action in selected_actions),
        success=trajectory[-1] == goal,
        trajectory=tuple(trajectory),
        observation_count=len(observation_rows),
        map_update_count=len(update_rows),
        safety_rejection_count=sum(len(record.safety_rejections) for record in decisions),
        initial_mean_entropy=initial_entropy,
        final_mean_entropy=float(np.mean(belief.entropy)),
        information_gained=initial_entropy - float(np.mean(belief.entropy)),
        decision_records=tuple(record.to_dict() for record in decisions),
    )

    root = Path(output_dir)
    _write_rows(root / "raw" / "observation_history.csv", observation_rows)
    _write_rows(root / "raw" / "map_update_events.csv", update_rows)
    report_path = root / "reports" / "belief_space_reasoning.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
    return result
