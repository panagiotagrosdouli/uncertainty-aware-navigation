"""Active-perception action scoring for approximate belief-space navigation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ActionType(StrEnum):
    MOVE_TOWARD_GOAL = "MOVE_TOWARD_GOAL"
    REPLAN = "REPLAN"
    OBSERVE = "OBSERVE"
    MOVE_TO_VIEWPOINT = "MOVE_TO_VIEWPOINT"
    WAIT_FOR_MEASUREMENT = "WAIT_FOR_MEASUREMENT"
    RETURN_TO_SAFE_REGION = "RETURN_TO_SAFE_REGION"
    STOP = "STOP"


@dataclass(frozen=True)
class PerceptionCandidate:
    identifier: str
    action: ActionType
    expected_information_gain: float
    travel_cost: float
    expected_risk: float
    resulting_recoverability: float
    expected_mission_delay: float


@dataclass(frozen=True)
class ScoredPerceptionCandidate:
    candidate: PerceptionCandidate
    utility: float


def score_candidate(
    candidate: PerceptionCandidate,
    information_weight: float = 2.0,
    risk_weight: float = 4.0,
    recoverability_weight: float = 2.0,
    delay_weight: float = 0.5,
) -> ScoredPerceptionCandidate:
    utility = (
        information_weight * candidate.expected_information_gain
        + recoverability_weight * candidate.resulting_recoverability
        - candidate.travel_cost
        - risk_weight * candidate.expected_risk
        - delay_weight * candidate.expected_mission_delay
    )
    return ScoredPerceptionCandidate(candidate, float(utility))


def select_action(candidates: list[PerceptionCandidate]) -> ScoredPerceptionCandidate:
    """Select maximum-utility candidate using deterministic identifier tie-break."""
    if not candidates:
        stop = PerceptionCandidate("no-safe-action", ActionType.STOP, 0.0, 0.0, 0.0, 1.0, 0.0)
        return score_candidate(stop)
    scored = [score_candidate(candidate) for candidate in candidates]
    return max(scored, key=lambda item: (item.utility, item.candidate.identifier))


def concise_explanation(selected: ScoredPerceptionCandidate) -> str:
    candidate = selected.candidate
    return (
        f"{candidate.action} selected: information_gain={candidate.expected_information_gain:.3f}, "
        f"risk={candidate.expected_risk:.3f}, recoverability={candidate.resulting_recoverability:.3f}, "
        f"travel_cost={candidate.travel_cost:.3f}, delay={candidate.expected_mission_delay:.3f}, "
        f"utility={selected.utility:.3f}."
    )
