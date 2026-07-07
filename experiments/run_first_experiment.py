"""Run the first uncertainty-aware navigation experiment.

The experiment compares classical A* with uncertainty-weighted risk-aware A*
on controlled grid-map environments.
"""
from __future__ import annotations

import time
from dataclasses import asdict
from pathlib import Path

import pandas as pd
import yaml

from uncertainty_navigation.environment import generate_random_grid
from uncertainty_navigation.metrics import evaluate_path
from uncertainty_navigation.planner import plan_path
from uncertainty_navigation.visualization import plot_map_with_path, plot_uncertainty_map

CONFIG_PATH = Path("configs/first_experiment.yaml")


def load_config(path: Path = CONFIG_PATH) -> dict:
    """Load the experiment configuration."""

    with path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def timed_plan(*args, **kwargs):
    """Run a planner and return both result and runtime."""

    start_time = time.perf_counter()
    result = plan_path(*args, **kwargs)
    runtime = time.perf_counter() - start_time
    return result, runtime


def main() -> None:
    """Run the first reproducible baseline experiment."""

    config = load_config()
    experiment_name = config["experiment"]["name"]
    output_dir = Path(config["outputs"]["directory"])
    figures_dir = output_dir / "figures"
    output_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    map_config = config["map"]
    lambda_values = config["planning"]["lambda_uncertainty"]
    seeds = config["trials"]["random_seeds"]

    records: list[dict] = []

    print(f"Loaded experiment: {experiment_name}")

    for seed in seeds:
        environment = generate_random_grid(
            width=map_config["width"],
            height=map_config["height"],
            obstacle_density=map_config["obstacle_density"],
            uncertainty_level=map_config["uncertainty_level"],
            seed=seed,
        )

        baseline_result, baseline_runtime = timed_plan(
            planner_name="astar",
            occupancy=environment.occupancy,
            uncertainty=environment.uncertainty,
            start=environment.start,
            goal=environment.goal,
        )
        baseline_metrics = evaluate_path(
            baseline_result.path,
            environment.occupancy,
            environment.uncertainty,
        )
        records.append(
            {
                "seed": seed,
                "planner": baseline_result.planner_name,
                "lambda_uncertainty": 0.0,
                "runtime_seconds": baseline_runtime,
                **asdict(baseline_metrics),
            }
        )

        if seed == seeds[0]:
            plot_map_with_path(
                environment.occupancy,
                baseline_result.path,
                figures_dir / "baseline_astar_path.png",
                title="Baseline A* path",
            )
            plot_uncertainty_map(
                environment.uncertainty,
                figures_dir / "uncertainty_map.png",
                title="Uncertainty map",
            )

        for lambda_uncertainty in lambda_values:
            if lambda_uncertainty == 0.0:
                continue

            risk_result, risk_runtime = timed_plan(
                planner_name="risk_aware_astar",
                occupancy=environment.occupancy,
                uncertainty=environment.uncertainty,
                start=environment.start,
                goal=environment.goal,
                lambda_uncertainty=lambda_uncertainty,
            )
            risk_metrics = evaluate_path(
                risk_result.path,
                environment.occupancy,
                environment.uncertainty,
            )
            records.append(
                {
                    "seed": seed,
                    "planner": risk_result.planner_name,
                    "lambda_uncertainty": lambda_uncertainty,
                    "runtime_seconds": risk_runtime,
                    **asdict(risk_metrics),
                }
            )

            if seed == seeds[0] and lambda_uncertainty == max(lambda_values):
                plot_map_with_path(
                    environment.occupancy,
                    risk_result.path,
                    figures_dir / "risk_aware_astar_path.png",
                    title=f"Risk-aware A* path, lambda={lambda_uncertainty}",
                )

    results = pd.DataFrame.from_records(records)
    results_path = output_dir / "metrics.csv"
    summary_path = output_dir / "summary.csv"
    results.to_csv(results_path, index=False)

    summary = results.groupby(["planner", "lambda_uncertainty"], as_index=False).agg(
        success_rate=("success", "mean"),
        mean_path_length=("path_length", "mean"),
        std_path_length=("path_length", "std"),
        mean_accumulated_risk_cost=("accumulated_risk_cost", "mean"),
        std_accumulated_risk_cost=("accumulated_risk_cost", "std"),
        mean_runtime_seconds=("runtime_seconds", "mean"),
        std_runtime_seconds=("runtime_seconds", "std"),
    )
    summary.to_csv(summary_path, index=False)

    print(f"Saved metrics: {results_path}")
    print(f"Saved summary: {summary_path}")
    print(f"Saved figures: {figures_dir}")


if __name__ == "__main__":
    main()
