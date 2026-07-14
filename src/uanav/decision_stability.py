from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class DecisionSnapshot:
    timestamp_s: float
    selected_action: str
    selected_route: str
    supervisor_state: str
    action_score: float
    alternative_score: float

    @property
    def score_margin(self) -> float:
        return self.alternative_score - self.action_score


@dataclass(frozen=True)
class StabilityDiagnostics:
    route_switches: int
    action_switches: int
    supervisor_transitions: int
    repeated_replans: int
    low_margin_decisions: int
    mean_score_margin: float
    oscillation_rate: float


@dataclass(frozen=True)
class HysteresisConfig:
    minimum_improvement: float = 0.1
    minimum_dwell_s: float = 1.0
    emergency_states: tuple[str, ...] = ("EMERGENCY_STOP", "MISSION_ABORT")


@dataclass(frozen=True)
class Counterfactual:
    variable: str
    observed_value: float
    threshold_value: float
    required_change: float
    statement: str


def analyze_decision_stability(
    snapshots: Sequence[DecisionSnapshot],
    low_margin_threshold: float = 0.1,
) -> StabilityDiagnostics:
    if not snapshots:
        return StabilityDiagnostics(0, 0, 0, 0, 0, 0.0, 0.0)
    route_switches = sum(
        a.selected_route != b.selected_route for a, b in zip(snapshots, snapshots[1:], strict=False)
    )
    action_switches = sum(
        a.selected_action != b.selected_action for a, b in zip(snapshots, snapshots[1:], strict=False)
    )
    supervisor_transitions = sum(
        a.supervisor_state != b.supervisor_state for a, b in zip(snapshots, snapshots[1:], strict=False)
    )
    repeated_replans = sum(
        a.selected_action == b.selected_action == "REPLAN" for a, b in zip(snapshots, snapshots[1:], strict=False)
    )
    margins = [snapshot.score_margin for snapshot in snapshots]
    low_margin_decisions = sum(margin < low_margin_threshold for margin in margins)
    transition_count = max(1, len(snapshots) - 1)
    oscillation_rate = action_switches / transition_count
    return StabilityDiagnostics(
        route_switches=route_switches,
        action_switches=action_switches,
        supervisor_transitions=supervisor_transitions,
        repeated_replans=repeated_replans,
        low_margin_decisions=low_margin_decisions,
        mean_score_margin=sum(margins) / len(margins),
        oscillation_rate=oscillation_rate,
    )


def apply_hysteresis(
    previous: DecisionSnapshot,
    proposed: DecisionSnapshot,
    config: HysteresisConfig | None = None,
) -> DecisionSnapshot:
    if config is None:
        config = HysteresisConfig()
    if proposed.supervisor_state in config.emergency_states:
        return proposed
    dwell_s = proposed.timestamp_s - previous.timestamp_s
    improvement = previous.action_score - proposed.action_score
    if dwell_s < config.minimum_dwell_s or improvement < config.minimum_improvement:
        return DecisionSnapshot(
            timestamp_s=proposed.timestamp_s,
            selected_action=previous.selected_action,
            selected_route=previous.selected_route,
            supervisor_state=proposed.supervisor_state,
            action_score=previous.action_score,
            alternative_score=proposed.action_score,
        )
    return proposed


def threshold_counterfactual(
    variable: str,
    observed_value: float,
    threshold_value: float,
    accepted_when_below: bool,
    accepted_statement: str,
) -> Counterfactual | None:
    rejected = observed_value > threshold_value if accepted_when_below else observed_value < threshold_value
    if not rejected:
        return None
    required_change = threshold_value - observed_value
    comparator = "at most" if accepted_when_below else "at least"
    return Counterfactual(
        variable=variable,
        observed_value=observed_value,
        threshold_value=threshold_value,
        required_change=required_change,
        statement=(
            f"{accepted_statement} if {variable} were {comparator} {threshold_value:.3f} "
            f"instead of {observed_value:.3f}."
        ),
    )


def grounded_counterfactuals(
    localization_trace: float,
    max_localization_trace: float,
    risk_bound: float,
    max_risk_bound: float,
    map_entropy: float,
    active_perception_threshold: float,
    viability: float,
    minimum_viability: float,
) -> tuple[Counterfactual, ...]:
    candidates = (
        threshold_counterfactual(
            "localization covariance trace",
            localization_trace,
            max_localization_trace,
            True,
            "The robot would continue without localization-triggered slowdown",
        ),
        threshold_counterfactual(
            "calibrated risk bound",
            risk_bound,
            max_risk_bound,
            True,
            "The candidate route would pass the risk constraint",
        ),
        threshold_counterfactual(
            "map entropy",
            map_entropy,
            active_perception_threshold,
            True,
            "Active perception would be unnecessary",
        ),
        threshold_counterfactual(
            "viability score",
            viability,
            minimum_viability,
            False,
            "The action would retain an admissible recovery option",
        ),
    )
    return tuple(candidate for candidate in candidates if candidate is not None)


def write_stability_evidence(
    output_path: str | Path,
    diagnostics: StabilityDiagnostics,
    counterfactuals: Sequence[Counterfactual],
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": "Synthetic Validation",
        "decision_stability": asdict(diagnostics),
        "counterfactuals": [asdict(counterfactual) for counterfactual in counterfactuals],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path
