"""Run online uncertainty-aware navigation experiments."""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import pandas as pd
import yaml

from uncertainty_navigation.environment import generate_random_grid
from uncertainty_navigation.result_summary import summarize_results
from uncertainty_navigation.simulation import SimulationConfig, run_online_navigation
from uncertainty_navigation.visualization import plot_map_with_path

CONFIG_PATH = Path("configs/online_navigation_experiment.yaml")


def load_config(path: Path = CONFIG_PATH) -> dict:
    """Load the experiment configuration."""

    with path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def main() -> None:
    """Run the online navigation experiment."""

    config = load_config()
    experiment_name = config["experiment"]["name"]
    output_dir = Path(config["outputs"]["directory"])
    figures_dir = output_dir / "figures"
    output_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    map_config = config["map"]
    sensor_config = config["sensor"]
    planning_config = config["planning"]
    simulation_config = config["simulation"]
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

        for planner_name in planning_config["planners"]:
            lambda_values = [0.0] if planner_name == "astar" else planning_config["lambda_uncertainty"]
            mu_values = [0.0] if planner_name == "astar" else planning_config["mu_occupancy"]

            for lambda_uncertainty in lambda_values:
                for mu_occupancy in mu_values:
                    rollout_config = SimulationConfig(
                        planner_name=planner_name,
                        lambda_uncertainty=lambda_uncertainty,
                        mu_occupancy=mu_occupancy,
                        sensor_radius=sensor_config["radius"],
                        max_steps=simulation_config["max_steps"],
                        treat_unknown_as_free=sensor_config["treat_unknown_as_free"],
                    )
                    result = run_online_navigation(
                        ground_truth_occupancy=environment.occupancy,
                        start=environment.start,
                        goal=environment.goal,
                        config=rollout_config,
                    )
                    records.append(
                        {
                            "seed": seed,
                            "planner": planner_name,
                            "lambda_uncertainty": lambda_uncertainty,
                            "mu_occupancy": mu_occupancy,
                            "sensor_radius": sensor_config["radius"],
                            **asdict(result),
                        }
                    )

                    should_plot = seed == seeds[0] and (
                        planner_name == "astar"
                        or (
                            lambda_uncertainty == max(planning_config["lambda_uncertainty"])
                            and mu_occupancy == max(planning_config["mu_occupancy"])
                        )
                    )
                    if should_plot:
                        figure_name = (
                            f"{planner_name}_lambda_{lambda_uncertainty}"
                            f"_mu_{mu_occupancy}_executed_path.png"
                        )
                        plot_map_with_path(
                            environment.occupancy,
                            result.path_history,
                            figures_dir / figure_name,
                            title=(
                                f"Executed path: {planner_name}, "
                                f"lambda={lambda_uncertainty}, mu={mu_occupancy}"
                            ),
                        )

    results = pd.DataFrame.from_records(records)
    results_path = output_dir / "metrics.csv"
    summary_path = output_dir / "summary.csv"
    ci_summary_path = output_dir / "summary_ci.csv"
    results.to_csv(results_path, index=False)

    metrics = [
        "steps",
        "replans",
        "collisions",
        "final_coverage",
        "final_mean_uncertainty",
        "mean_executed_occupancy_probability",
    ]
    summary = summarize_results(
        df=results,
        group_by=["planner", "lambda_uncertainty", "mu_occupancy"],
        metrics=metrics,
        success_column="success",
        compute_ci=False,
    )
    summary.to_csv(summary_path, index=False)

    ci_summary = summarize_results(
        df=results,
        group_by=["planner", "lambda_uncertainty", "mu_occupancy"],
        metrics=metrics,
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
