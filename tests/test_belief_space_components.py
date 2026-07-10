import numpy as np

from uanav.active_perception.planner import ActionType, PerceptionCandidate, select_action
from uanav.dynamics.prediction import DynamicAgent, path_dynamic_risk, predict_dynamic_risk
from uanav.safety.constraints import CandidateSafetyState, evaluate_constraints
from uanav.uncertainty.predictive import predict_path_uncertainty


def test_predictive_uncertainty_observation_reduces_entropy() -> None:
    entropy = np.full((3, 3), 0.8)
    mask = np.zeros((3, 3), dtype=bool)
    mask[1, 1] = True
    result = predict_path_uncertainty([(0, 0), (1, 1), (2, 2)], entropy, mask)
    assert result.observation_opportunities == 1
    assert result.expected_information_gain > 0
    assert result.post_observation_uncertainty[1] < entropy[1, 1]


def test_active_perception_can_prefer_viewpoint() -> None:
    candidates = [
        PerceptionCandidate("goal", ActionType.MOVE_TOWARD_GOAL, 0.0, 1.0, 0.4, 0.3, 0.0),
        PerceptionCandidate("view", ActionType.MOVE_TO_VIEWPOINT, 1.2, 1.2, 0.05, 0.9, 0.5),
    ]
    selected = select_action(candidates)
    assert selected.candidate.action == ActionType.MOVE_TO_VIEWPOINT


def test_safety_layer_rejects_low_cost_unsafe_candidate() -> None:
    state = CandidateSafetyState(
        candidate_id="short-route",
        collision_probability=0.6,
        map_uncertainty=0.2,
        localization_uncertainty=0.2,
        minimum_clearance=2.0,
        fallback_path_exists=False,
        irrecoverable_state=False,
        safe_stop_reachable=True,
        timestep=4,
    )
    names = {item.violated_constraint for item in evaluate_constraints(state)}
    assert names == {"collision_probability", "fallback_path_exists"}


def test_dynamic_risk_changes_over_time() -> None:
    agent = DynamicAgent(position=(1.0, 0.0), velocity=(0.0, 1.0), position_std=0.2)
    layers = predict_dynamic_risk((3, 5), [agent], horizon=5)
    assert layers.shape == (5, 3, 5)
    assert layers[0, 1, 0] > layers[0, 1, 4]
    summary = path_dynamic_risk([(1, 0), (1, 1), (1, 2)], layers)
    assert summary["maximum_risk"] > 0.5
    assert 0.0 <= summary["blockage_probability"] <= 1.0
