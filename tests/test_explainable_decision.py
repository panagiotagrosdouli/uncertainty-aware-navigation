import numpy as np

from uanav.active_perception.planner import ActionType, PerceptionCandidate
from uanav.explainability import CandidateDecisionInput, evaluate_candidate, select_admissible_candidate


def _candidate(identifier: str, action: ActionType, risk: float, recoverability: float) -> PerceptionCandidate:
    return PerceptionCandidate(
        identifier=identifier,
        action=action,
        expected_information_gain=0.4,
        travel_cost=1.0,
        expected_risk=risk,
        resulting_recoverability=recoverability,
        expected_mission_delay=0.2,
    )


def test_low_cost_candidate_is_rejected_when_fallback_is_lost() -> None:
    probability = np.full((5, 7), 0.1)
    uncertainty = np.zeros_like(probability)
    probability[:, 3] = 0.95
    decision = CandidateDecisionInput(
        candidate=_candidate("unsafe-shortcut", ActionType.MOVE_TOWARD_GOAL, 0.01, 0.9),
        path=[(2, 1), (2, 2), (2, 3), (2, 4)],
        collision_probability=0.01,
        map_uncertainty=0.1,
        localization_uncertainty=0.1,
        minimum_clearance=2.0,
        timestep=4,
    )

    record = evaluate_candidate(
        decision,
        probability,
        uncertainty,
        safe_regions={(2, 1)},
        recoverability_threshold=0.0,
    )

    assert not record.admissible
    assert record.recoverability.first_irrecoverable_index == 2
    assert any(item.violated_constraint == "fallback_path_exists" for item in record.safety_rejections)
    assert "Fallback path is lost" in record.concise_explanation


def test_safe_viewpoint_candidate_is_selected_over_rejected_shortcut() -> None:
    probability = np.full((7, 7), 0.1)
    uncertainty = np.zeros_like(probability)
    unsafe = CandidateDecisionInput(
        candidate=_candidate("shortcut", ActionType.MOVE_TOWARD_GOAL, 0.35, 0.2),
        path=[(3, 3), (3, 4)],
        collision_probability=0.35,
        map_uncertainty=0.2,
        localization_uncertainty=0.2,
        minimum_clearance=2.0,
        timestep=2,
    )
    safe = CandidateDecisionInput(
        candidate=_candidate("viewpoint", ActionType.MOVE_TO_VIEWPOINT, 0.05, 0.9),
        path=[(3, 3), (2, 3), (2, 4)],
        collision_probability=0.05,
        map_uncertainty=0.2,
        localization_uncertainty=0.2,
        minimum_clearance=2.0,
        timestep=2,
    )

    records = [
        evaluate_candidate(unsafe, probability, uncertainty, safe_regions={(3, 1)}, recoverability_threshold=0.0),
        evaluate_candidate(safe, probability, uncertainty, safe_regions={(3, 1)}, recoverability_threshold=0.0),
    ]
    selected = select_admissible_candidate(records)

    assert selected is not None
    assert selected.candidate_id == "viewpoint"
    assert selected.selected_action == ActionType.MOVE_TO_VIEWPOINT
    assert "admissible" in selected.concise_explanation


def test_no_safe_candidate_returns_none() -> None:
    probability = np.full((5, 5), 0.1)
    uncertainty = np.zeros_like(probability)
    decision = CandidateDecisionInput(
        candidate=_candidate("too-risky", ActionType.REPLAN, 0.8, 0.1),
        path=[(2, 2), (2, 3)],
        collision_probability=0.8,
        map_uncertainty=0.9,
        localization_uncertainty=0.9,
        minimum_clearance=0.2,
        timestep=7,
    )
    record = evaluate_candidate(
        decision,
        probability,
        uncertainty,
        safe_regions={(2, 1)},
        recoverability_threshold=0.0,
    )

    assert select_admissible_candidate([record]) is None
    assert len(record.safety_rejections) >= 4
