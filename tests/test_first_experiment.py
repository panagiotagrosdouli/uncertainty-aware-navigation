import json
from pathlib import Path

from experiments.run_first_experiment import run_experiment


def test_first_experiment_writes_reproducibility_artifacts(tmp_path: Path) -> None:
    config = tmp_path / "config.yaml"
    output = tmp_path / "out"
    config.write_text(
        """
seeds: [1, 2]
lambda_uncertainty: 3.0
scenario:
  size: 12
  obstacle_density: 0.05
  uncertainty_noise: 0.2
  obstacle_threshold: 0.5
""".strip(),
        encoding="utf-8",
    )

    summary = run_experiment(config, output)

    assert "astar_shortest_path" in summary
    assert "uncertainty_aware_astar" in summary
    assert (output / "trials.csv").exists()
    assert (output / "summary.json").exists()
    assert (output / "manifest.json").exists()
    assert (output / "REPORT.md").exists()
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["seeds"] == [1, 2]
