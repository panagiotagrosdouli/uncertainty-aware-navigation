from scripts.run_all import run_mode


def test_belief_space_run_mode_executes(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = run_mode("belief-space")

    assert result["success"]
    assert result["selected_actions"] == ("MOVE_TO_VIEWPOINT", "REPLAN")
    assert result["safety_rejection_count"] > 0


def test_smoke_mode_executes_both_pipelines(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = run_mode("smoke")

    assert result["synthetic_success"]
    assert result["belief_space_success"]
