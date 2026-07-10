"""Explainable candidate evaluation with safety and recoverability rejection."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np

from uanav.active_perception.planner import PerceptionCandidate, ScoredPerceptionCandidate, score_candidate
from uanav.recoverability import RecoverabilityAssessment, assess_path_recoverability
from uanav.safety.constraints import CandidateSafetyState, SafetyRejection, SafetyThresholds, evaluate_constraints

Point = tuple[int, int]


@dataclass(frozen=True)
class CandidateDecisionInput:
    candidate: PerceptionCandidate
    path: list[Point]
    collision_probability: float
    map_uncertainty: float
    localization_uncertainty: float
    minimum_clearance: float
    timestep: int


@dataclass(frozen=True)
class CandidateDecisionRecord:
    candidate_id: str
    selected_action: str
    admissible: bool
    final_score: float
    recoverability: RecoverabilityAssessment
    safety_rejections: tuple[SafetyRejection, ...]
    concise_explanation: str

    def to_dict(self) -> dict:
        return asdict(self)


def evaluate_candidate(
    decision: CandidateDecisionInput,
    occupancy_probability: np.ndarray,
    uncertainty: np.ndarray,
    safe_regions: set[Point],
    safety_thresholds: SafetyThresholds | None = None,
    recoverability_threshold: float = 0.50,
) -> CandidateDecisionRecord:
    """Score a candidate, then apply independent hard safety constraints."""
    recovery = assess_path_recoverability(
        decision.candidate.identifier,
        decision.path,
        occupancy_probability,
        uncertainty,
        safe_regions,
        recoverability_threshold=recoverability_threshold,
    )
    safety_state = CandidateSafetyState(
        candidate_id=decision.candidate.identifier,
        collision_probability=decision.collision_probability,
        map_uncertainty=decision.map_uncertainty,
        localization_uncertainty=decision.localization_uncertainty,
        minimum_clearance=decision.minimum_clearance,
        fallback_path_exists=recovery.fallback_path_exists,
        irrecoverable_state=not recovery.admissible,
        safe_stop_reachable=recovery.safe_stop_reachable,
        timestep=decision.timestep,
    )
    rejections = tuple(evaluate_constraints(safety_state, safety_thresholds))
    scored: ScoredPerceptionCandidate = score_candidate(decision.candidate)
    admissible = recovery.admissible and not rejections

    if admissible:
        explanation = (
            f"{decision.candidate.action} is admissible with utility {scored.utility:.3f}; "
            f"fallback cost={recovery.fallback_path_cost:.1f}, "
            f"escape routes={recovery.escape_route_count}, "
            f"minimum clearance={recovery.minimum_future_clearance:.2f}."
        )
    else:
        reasons = [rejection.explanation for rejection in rejections]
        if recovery.rejection_reason and recovery.rejection_reason not in reasons:
            reasons.insert(0, recovery.rejection_reason)
        explanation = (
            f"{decision.candidate.action} rejected despite utility {scored.utility:.3f}: " + " ".join(reasons)
        )

    return CandidateDecisionRecord(
        candidate_id=decision.candidate.identifier,
        selected_action=str(decision.candidate.action),
        admissible=admissible,
        final_score=scored.utility,
        recoverability=recovery,
        safety_rejections=rejections,
        concise_explanation=explanation,
    )


def select_admissible_candidate(records: list[CandidateDecisionRecord]) -> CandidateDecisionRecord | None:
    """Return the highest-scoring admissible record with deterministic tie-breaking."""
    admissible = [record for record in records if record.admissible]
    if not admissible:
        return None
    return max(admissible, key=lambda record: (record.final_score, record.candidate_id))
