"""Explicit safety constraints separated from planner cost."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SafetyThresholds:
    max_collision_probability: float = 0.20
    max_map_uncertainty: float = 0.75
    max_localization_uncertainty: float = 0.80
    min_clearance: float = 1.0
    require_fallback_path: bool = True
    require_safe_stop_reachable: bool = True


@dataclass(frozen=True)
class CandidateSafetyState:
    candidate_id: str
    collision_probability: float
    map_uncertainty: float
    localization_uncertainty: float
    minimum_clearance: float
    fallback_path_exists: bool
    irrecoverable_state: bool
    safe_stop_reachable: bool
    timestep: int


@dataclass(frozen=True)
class SafetyRejection:
    candidate_id: str
    violated_constraint: str
    measured_value: float | bool
    permitted_threshold: float | bool
    timestep: int
    explanation: str


def evaluate_constraints(
    state: CandidateSafetyState,
    thresholds: SafetyThresholds | None = None,
) -> list[SafetyRejection]:
    """Return every violated constraint; an empty result means admissible."""
    limits = SafetyThresholds() if thresholds is None else thresholds
    checks: list[tuple[bool, str, float | bool, float | bool, str]] = [
        (
            state.collision_probability <= limits.max_collision_probability,
            "collision_probability",
            state.collision_probability,
            limits.max_collision_probability,
            "Predicted collision probability proxy exceeds the permitted threshold.",
        ),
        (
            state.map_uncertainty <= limits.max_map_uncertainty,
            "map_uncertainty",
            state.map_uncertainty,
            limits.max_map_uncertainty,
            "Candidate enters a region with excessive map uncertainty.",
        ),
        (
            state.localization_uncertainty <= limits.max_localization_uncertainty,
            "localization_uncertainty",
            state.localization_uncertainty,
            limits.max_localization_uncertainty,
            "Predicted localization uncertainty is too high.",
        ),
        (
            state.minimum_clearance >= limits.min_clearance,
            "minimum_clearance",
            state.minimum_clearance,
            limits.min_clearance,
            "Candidate violates minimum obstacle-clearance requirements.",
        ),
        (
            not limits.require_fallback_path or state.fallback_path_exists,
            "fallback_path_exists",
            state.fallback_path_exists,
            True,
            "No safe fallback path remains reachable.",
        ),
        (
            not state.irrecoverable_state,
            "irrecoverable_state",
            state.irrecoverable_state,
            False,
            "Candidate enters a known irrecoverable state.",
        ),
        (
            not limits.require_safe_stop_reachable or state.safe_stop_reachable,
            "safe_stop_reachable",
            state.safe_stop_reachable,
            True,
            "A safe stopping state would no longer remain reachable.",
        ),
    ]
    return [
        SafetyRejection(
            candidate_id=state.candidate_id,
            violated_constraint=name,
            measured_value=value,
            permitted_threshold=threshold,
            timestep=state.timestep,
            explanation=explanation,
        )
        for passed, name, value, threshold, explanation in checks
        if not passed
    ]
