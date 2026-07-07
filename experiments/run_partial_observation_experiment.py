"""Run a partial-observation uncertainty-aware navigation experiment.

This experiment creates uncertainty from limited sensor visibility instead of
using purely random uncertainty values. Planning is performed on the partially
observed map, while safety is evaluated against the ground-truth map.
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
from uncertainty_navigation.result_summary import summarize_results
from uncertainty_navigation.sensor_model import (
    observe_occupancy,
    planning_occupancy_from_partial,
    uncertainty_from_observation,
)
from uncertainty_navigation.visualization import plot_map_with_path, plot_uncertainty_map

CONFIG_PATH = Path("configs/partial_observation_experiment.yaml")


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
    """Run the partial-observation experiment."""

    config = load_config()
    experiment_name = config["experiment"]["name"]
    output_dir = Path(config["outputs"]["directory"])
    figures_dir = output_dir / "figures"
    output_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    map_config = config["map"]
    sensor_config = config["sensor"]
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

        observed_occupancy = observe_occupancy(
            ground_truth_occupancy=environment.occupancy,
            position=environment.start,
            radius=sensor_config["radius"],
        )
        uncertainty = uncertainty_from_observation(observed_occupancy)
        planning_occupancy = planning_occupancy_from_partial(
            observed_occupancy,
            treat_unknown_as_free=sensor_config["treat_unknown_as_free"],
        )

        baseline_result, baseline_runtime = timed_plan(
            planner_name="astar",
            occupancy=planning_occupancy,
            uncertainty=uncertainty,
            start=environment.start,
            goal=environment.goal,
        )
        baseline_metrics = evaluate_path(
            baseline_result.path,
            environment.occupancy,
            uncertainty,
        )
        records.append(
            {
                "seed": seed,
                "planner": baseline_result.planner_name,
                "lambda_uncertainty": 0.0,
                "sensor_radius": sensor_config["radius"],
                "runtime_seconds": baseline_runtime,
                **asdict(baseline_metrics),
            }
        )

        if seed == seeds[0]:
            plot_map_with_path(
                planning_occupancy,
                baseline_result.path,
                figures_dir / "baseline_partial_observation_path.png",
                title="Baseline A* path on partially observed map",
            )
            plot_uncertainty_map(
                uncertainty,
                figures_dir / "partial_observation_uncertainty.png",
                title="Uncertainty from partial observation",
            )
            plot_map_with_path(
                environment.occupancy,
                baseline_result.path,
                figures_dir / "baseline_path_on_ground_truth.png",
                title="Baseline A* path evaluated on ground truth",
            )

        for lambda_uncertainty in lambda_values:
            if lambda_uncertainty == 0.0:
                continue

            risk_result, risk_runtime = timed_plan(
                planner_name="risk_aware_astar",
                occupancy=planning_occupancy,
                uncertainty=uncertainty,
                start=environment.start,
                goal=environment.goal,
                lambda_uncertainty=lambda_uncertainty,
            )
            risk_metrics = evaluate_path(
                risk_result.path,
                environment.occupancy,
                uncertainty,
            )
            records.append(
                {
                    "seed": seed,
                    "planner": risk_result.planner_name,
                    "lambda_uncertainty": lambda_uncertainty,
                    "sensor_radius": sensor_config["radius"],
                    "runtime_seconds": risk_runtime,
                    **asdict(risk_metrics),
                }
            )

            if seed == seeds[0] and lambda_uncertainty == max(lambda_values):
                plot_map_with_path(
                    planning_occupancy,
                    risk_result.path,
                    figures_dir / "risk_aware_partial_observation_path.png",
                    title=f"Risk-aware A* on partial map, lambda={lambda_uncertainty}",
                )
                plot_map_with_path(
                    environment.occupancy,
                    risk_result.path,
                    figures_dir / "risk_aware_path_on_ground_truth.png",
                    title=f"Risk-aware path evaluated on ground truth, lambda={lambda_uncertainty}",
                )

    results = pd.DataFrame.from_records(records)
    results_path = output_dir / "metrics.csv"
    summary_path = output_dir / "summary.csv"
    ci_summary_path = output_dir / "summary_ci.csv"
    results.to_csv(results_path, index=False)

    summary = summarize_results(
        df=results,
        group_by=["planner", "lambda_uncertainty"],
        metrics=["path_length", "accumulated_risk_cost", "collision_count", "runtime_seconds"],
        success_column="success",
        compute_ci=False,
    )
    summary.to_csv(summary_path, index=False)

    ci_summary = summarize_results(
        df=results,
        group_by=["planner", "lambda_uncertainty"],
        metrics=["path_length", "accumulated_risk_cost", "collision_count", "runtime_seconds"],
        success_column="success",
        compute_ci=True,
        ci_iterations=1000,
    )
    ci_summary.to_csv(ci_summary_path, index=False)

    print(f"Saved metrics: {results_path}")
    print(f"Saved summary: {summary_path}")
    print(f"Saved CI summary: {ci_summary_path}")
    print(f"Saved figures: {figures_dir}")


if __name__ == "__main__":
    main()
