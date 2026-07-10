import json

from uanav.active_perception.planner import ActionType
from uanav.belief_space import run_belief_space_demo


def test_online_belief_space_loop_selects_viewpoint_and_replans(tmp_path) -> None:
    result = run_belief_space_demo(tmp_path)

    assert result.success
    assert result.selected_actions == (
        str(ActionType.MOVE_TO_VIEWPOINT),
        str(ActionType.REPLAN),
    )
    assert result.observation_count > 0
    assert result.map_update_count == result.observation_count
    assert result.information_gained > 0
    assert result.final_mean_entropy < result.initial_mean_entropy
    assert result.safety_rejection_count > 0

    observation_history = tmp_path / "raw" / "observation_history.csv"
    map_updates = tmp_path / "raw" / "map_update_events.csv"
    reasoning = tmp_path / "reports" / "belief_space_reasoning.json"
    assert observation_history.exists()
    assert map_updates.exists()
    assert reasoning.exists()

    payload = json.loads(reasoning.read_text(encoding="utf-8"))
    direct_after = [record for record in payload["decision_records"] if record["candidate_id"] == "direct"][-1]
    assert not direct_after["admissible"]
    assert direct_after["safety_rejections"]
    assert "rejected despite utility" in direct_after["concise_explanation"]
