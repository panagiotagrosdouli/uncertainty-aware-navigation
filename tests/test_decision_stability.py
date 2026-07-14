import json

import pytest

from uanav.decision_stability import (
    DecisionSnapshot,
    HysteresisConfig,
    analyze_decision_stability,
    apply_hysteresis,
    grounded_counterfactuals,
    write_stability_evidence,
)


def test_stability_diagnostics_count_switches_and_replans() -> None:
    snapshots = (
        DecisionSnapshot(0.0, "MOVE", "north", "NORMAL", 1.0, 1.3),
        DecisionSnapshot(1.0, "REPLAN", "south", "REPLAN", 1.1, 1.15),
        DecisionSnapshot(2.0, "REPLAN", "south", "REPLAN", 1.0, 1.04),
        DecisionSnapshot(3.0, "MOVE", "north", "NORMAL", 0.8, 1.2),
    )
    diagnostics = analyze_decision_stability(snapshots, low_margin_threshold=0.1)
    assert diagnostics.route_switches == 2
    assert diagnostics.action_switches == 2
    assert diagnostics.supervisor_transitions == 2
    assert diagnostics.repeated_replans == 1
    assert diagnostics.low_margin_decisions == 2


def test_hysteresis_keeps_previous_action_without_sufficient_improvement() -> None:
    previous = DecisionSnapshot(0.0, "MOVE", "north", "NORMAL", 1.0, 1.2)
    proposed = DecisionSnapshot(0.5, "REPLAN", "south", "REPLAN", 0.95, 1.0)
    selected = apply_hysteresis(previous, proposed, HysteresisConfig(0.1, 1.0))
    assert selected.selected_action == "MOVE"
    assert selected.selected_route == "north"
    assert selected.supervisor_state == "REPLAN"


def test_hysteresis_never_blocks_emergency_override() -> None:
    previous = DecisionSnapshot(0.0, "MOVE", "north", "NORMAL", 1.0, 1.2)
    proposed = DecisionSnapshot(0.1, "STOP", "none", "EMERGENCY_STOP", 2.0, 2.1)
    assert apply_hysteresis(previous, proposed) == proposed


def test_counterfactuals_are_computed_from_actual_thresholds(tmp_path) -> None:
    counterfactuals = grounded_counterfactuals(
        localization_trace=0.7,
        max_localization_trace=0.5,
        risk_bound=0.52,
        max_risk_bound=0.45,
        map_entropy=0.65,
        active_perception_threshold=0.4,
        viability=0.3,
        minimum_viability=0.5,
    )
    assert len(counterfactuals) == 4
    assert counterfactuals[0].required_change == pytest.approx(-0.2)
    assert counterfactuals[-1].required_change == pytest.approx(0.2)
    output = write_stability_evidence(
        tmp_path / "stability.json",
        analyze_decision_stability(()),
        counterfactuals,
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == "Synthetic Validation"
    assert payload["counterfactuals"][1]["threshold_value"] == 0.45
