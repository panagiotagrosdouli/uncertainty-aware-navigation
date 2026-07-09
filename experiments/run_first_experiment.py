"""Run the first uncertainty-aware navigation experiment.

The script intentionally produces raw CSV, aggregate JSON, and a manifest. It does
not print benchmark claims; users should inspect and cite the generated artifacts.
"""

from __future__ import annotations

import argparse
import csv
import json
import platform
import subprocess
from dataclasses import asdict
from pathlib import Path
from statistics import mean, pstdev
from typing import Any

import yaml

from uncertainty_navigation.evaluation import evaluate_path
from uncertainty_navigation.planning import GridPlanner
from uncertainty_navigation.simulation import ScenarioConfig, make_synthetic_grid


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/first_experiment.yaml"))
    parser.add_argument("--output", type=Path, default=Path("results/first_experiment"))
    args = parser.parse_args()

    config = _load_config(args.config)
    args.output.mkdir(parents=True, exist_ok=True)

    seeds = [int(seed) for seed in config.get("seeds", [0, 1, 2, 3, 4])]
    scenario_cfg = ScenarioConfig(**config.get("scenario", {}))
    planners = [
        GridPlanner(name="astar_shortest_path", lambda_uncertainty=0.0, lambda_occupancy=0.0),
        GridPlanner(
            name="uncertainty_aware_astar",
            lambda_uncertainty=float(config.get("lambda_uncertainty", 4.0)),
            lambda_occupancy=float(config.get("lambda_occupancy", 0.0)),
        ),
    ]

    rows: list[dict[str, Any]] = []
    for seed in seeds:
        grid, start, goal = make_synthetic_grid(seed, scenario_cfg)
        for planner in planners:
            result = planner.plan(grid, start, goal)
            metrics = evaluate_path(seed, grid, result)
            rows.append(asdict(metrics))

    raw_csv = args.output / "trials.csv"
    _write_csv(raw_csv, rows)
    summary = _summarize(rows)
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    manifest = _manifest(args.config, args.output, seeds, config)
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    _write_report(args.output / "REPORT.md", summary, manifest)


def _load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing experiment config: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("experiment config must be a mapping")
    return data


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError("no experiment rows generated")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _summarize(rows: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    summary: dict[str, dict[str, float]] = {}
    planners = sorted({str(row["planner"]) for row in rows})
    numeric_fields = [
        "success",
        "collision",
        "path_length",
        "accumulated_uncertainty",
        "accumulated_occupancy",
        "min_obstacle_distance",
        "expanded_nodes",
        "runtime_s",
        "cost",
    ]
    for planner in planners:
        planner_rows = [row for row in rows if row["planner"] == planner]
        summary[planner] = {}
        for field in numeric_fields:
            values = [float(row[field]) for row in planner_rows]
            summary[planner][f"{field}_mean"] = mean(values)
            summary[planner][f"{field}_std"] = pstdev(values) if len(values) > 1 else 0.0
    return summary


def _manifest(config_path: Path, output_path: Path, seeds: list[int], config: dict[str, Any]) -> dict[str, Any]:
    return {
        "config_path": str(config_path),
        "output_path": str(output_path),
        "seeds": seeds,
        "config": config,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "git_commit": _git_commit(),
    }


def _git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:  # pragma: no cover - best-effort metadata outside git clones
        return "unknown"


def _write_report(path: Path, summary: dict[str, dict[str, float]], manifest: dict[str, Any]) -> None:
    lines = [
        "# First Experiment Report",
        "",
        "This report is generated automatically from `experiments/run_first_experiment.py`.",
        "It is a synthetic diagnostic experiment, not real-robot validation.",
        "",
        "## Manifest",
        "",
        f"- Config: `{manifest['config_path']}`",
        f"- Seeds: `{manifest['seeds']}`",
        f"- Git commit: `{manifest['git_commit']}`",
        "",
        "## Aggregate metrics",
        "",
    ]
    for planner, metrics in summary.items():
        lines.extend([f"### {planner}", ""])
        for key, value in metrics.items():
            lines.append(f"- `{key}`: {value:.6g}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
