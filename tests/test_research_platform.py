from uanav.research_platform import (
    CandidatePath,
    DynamicObstacle,
    Pose2D,
    SupervisorState,
    adaptive_sample_count,
    cvar,
    estimate_risk,
    predict_constant_velocity,
    run_research_smoke,
    shield,
    split_conformal_absolute,
    viability_score,
)


def test_cvar_focuses_on_tail() -> None:
    assert cvar([0.0, 0.1, 0.2, 0.9, 1.0], 0.8) == 1.0


def test_conformal_reports_coverage() -> None:
    result = split_conformal_absolute([0.1] * 9, [0.05, 0.12], 0.9)
    assert result.quantile == 0.1
    assert result.empirical_coverage == 0.5
    assert result.coverage_violation == 0.4


def test_prediction_grows_covariance() -> None:
    obstacle = DynamicObstacle("o", Pose2D(0, 0, 0), (1, 0))
    prediction = predict_constant_velocity(obstacle, 1.0, 0.5)
    assert prediction[-1].x_m == 1.0
    assert prediction[-1].covariance_trace_m2 > prediction[0].covariance_trace_m2


def test_viability_rejects_dead_end_and_shield_overrides() -> None:
    path = CandidatePath("dead-end", ((0, 0), (1, 0)), 1, 0, 0, 0)
    viability = viability_score(path, 0.1, 0, False)
    risk = estimate_risk([0.1, 0.2], 0.05)
    decision = shield(risk, 0.1, 0.1, viability >= 0.5, True)
    assert decision.state == SupervisorState.RECOVERY
    assert not decision.allow_motion


def test_adaptive_sampling_increases_under_difficulty() -> None:
    easy = adaptive_sample_count(0.5, 1, 0.1, False)
    hard = adaptive_sample_count(0.05, 3, 0.6, True)
    assert hard > easy


def test_research_smoke_selects_viable_fallback(tmp_path) -> None:
    result = run_research_smoke(tmp_path)
    assert result["selected_candidate"] == "fallback"
    assert (tmp_path / "research_smoke.json").exists()
    direct = next(r for r in result["candidates"] if r["candidate_id"] == "direct")
    assert direct["safety"]["state"] in {"RECOVERY", "REPLAN"}
