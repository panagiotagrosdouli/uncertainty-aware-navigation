from pathlib import Path

import numpy as np

from uanav.demo import ScenarioConfig, astar, build_world, generate_figures, make_demo_media, run_synthetic_demo, validate_path


def test_synthetic_world_maps_and_planner(tmp_path):
    cfg = ScenarioConfig(output_dir=str(tmp_path))
    occ, belief, unknown, uncertainty, risk, recoverability = build_world(cfg)
    assert occ.shape == (cfg.height, cfg.width)
    assert np.all((uncertainty >= 0) & (uncertainty <= 1))
    assert np.all((risk >= 0) & (risk <= 1))
    assert np.all((recoverability >= 0) & (recoverability <= 1))
    path, info = astar(occ, cfg.start, cfg.goal, uncertainty, risk, recoverability)
    assert validate_path(path, occ)
    assert info["planning_time_s"] >= 0


def test_run_all_artifact_smoke(tmp_path):
    result = run_synthetic_demo(ScenarioConfig(output_dir=str(tmp_path)))
    assert result["metrics"]["label"] == "Synthetic Demo"
    assert (tmp_path / "metrics" / "summary.json").exists()
    figures = generate_figures(result)
    assert figures
    gif, mp4 = make_demo_media(result)
    assert Path(gif).exists()
    assert Path(mp4).exists()
