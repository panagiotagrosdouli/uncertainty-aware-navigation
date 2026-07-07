"""Plotting utilities for experiment-level result analysis."""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def plot_metric_vs_lambda(
    summary: pd.DataFrame,
    metric_column: str,
    output_path: str | Path,
    title: str,
    ylabel: str,
) -> None:
    """Plot a summary metric against lambda for each occupancy-risk weight."""

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    risk_rows = summary[summary["planner"] == "risk_aware_astar"]

    plt.figure()
    for mu_occupancy, group in risk_rows.groupby("mu_occupancy"):
        group = group.sort_values("lambda_uncertainty")
        plt.plot(
            group["lambda_uncertainty"],
            group[metric_column],
            marker="o",
            label=f"mu={mu_occupancy}",
        )

    baseline = summary[summary["planner"] == "astar"]
    if not baseline.empty:
        baseline_value = float(baseline[metric_column].iloc[0])
        plt.axhline(baseline_value, linestyle="--", label="A* baseline")

    plt.xlabel("lambda_uncertainty")
    plt.ylabel(ylabel)
    plt.title(title)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=200)
    plt.close()


def create_online_summary_plots(summary: pd.DataFrame, output_dir: str | Path) -> None:
    """Create standard plots for the online navigation experiment."""

    output_dir = Path(output_dir)
    plot_specs = [
        (
            "success_rate",
            "success_rate_vs_lambda.png",
            "Success rate vs uncertainty weight",
            "success rate",
        ),
        (
            "collisions_mean",
            "collisions_vs_lambda.png",
            "Mean collisions vs uncertainty weight",
            "mean collisions",
        ),
        (
            "steps_mean",
            "steps_vs_lambda.png",
            "Mean execution steps vs uncertainty weight",
            "mean steps",
        ),
        (
            "final_mean_uncertainty_mean",
            "final_uncertainty_vs_lambda.png",
            "Final mean uncertainty vs uncertainty weight",
            "final mean uncertainty",
        ),
        (
            "mean_executed_occupancy_probability_mean",
            "executed_occupancy_probability_vs_lambda.png",
            "Mean executed occupancy probability vs uncertainty weight",
            "mean executed P(occupied)",
        ),
    ]

    for metric_column, filename, title, ylabel in plot_specs:
        if metric_column in summary.columns:
            plot_metric_vs_lambda(
                summary=summary,
                metric_column=metric_column,
                output_path=output_dir / filename,
                title=title,
                ylabel=ylabel,
            )
