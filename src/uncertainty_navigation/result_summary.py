"""Reusable result summarization utilities for navigation experiments.

The design is inspired by the result-analysis tooling in DynNav, adapted here
as a package-level utility for this paper-style repository.
"""
from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd


def auto_numeric_metrics(df: pd.DataFrame, exclude: Sequence[str] | None = None) -> list[str]:
    """Return numeric columns suitable for aggregation."""

    excluded = set(exclude or [])
    return [
        column
        for column in df.columns
        if column not in excluded and pd.api.types.is_numeric_dtype(df[column])
    ]


def coerce_success(series: pd.Series) -> pd.Series:
    """Convert common success encodings to booleans."""

    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False)

    if pd.api.types.is_numeric_dtype(series):
        return series.fillna(0).astype(float) != 0.0

    normalized = series.astype(str).str.strip().str.lower()
    truthy = {"true", "1", "yes", "y", "success", "ok"}
    return normalized.apply(lambda value: value in truthy)


def bootstrap_mean_ci(
    values: pd.Series,
    iterations: int = 2000,
    alpha: float = 0.05,
    seed: int = 0,
) -> tuple[float, float]:
    """Compute a deterministic non-parametric bootstrap CI for a mean."""

    samples = pd.to_numeric(values, errors="coerce").dropna().to_numpy()
    sample_count = len(samples)
    if sample_count < 2:
        return float("nan"), float("nan")

    rng = np.random.default_rng(seed)
    means = np.empty(iterations, dtype=float)
    for index in range(iterations):
        resampled = rng.choice(samples, size=sample_count, replace=True)
        means[index] = float(np.mean(resampled))

    lower = float(np.quantile(means, alpha / 2))
    upper = float(np.quantile(means, 1 - alpha / 2))
    return lower, upper


def summarize_results(
    df: pd.DataFrame,
    group_by: Sequence[str] | str | None,
    metrics: Sequence[str] | None = None,
    success_column: str | None = "success",
    compute_ci: bool = False,
    ci_iterations: int = 2000,
    warn_small_n: bool = True,
) -> pd.DataFrame:
    """Summarize experiment results using mean, standard deviation, and success rate."""

    group_columns = [group_by] if isinstance(group_by, str) else list(group_by or [])
    missing_group_columns = [column for column in group_columns if column not in df.columns]
    if missing_group_columns:
        raise ValueError(f"Missing group columns: {missing_group_columns}")

    excluded = list(group_columns)
    if success_column:
        excluded.append(success_column)
    selected_metrics = list(metrics or auto_numeric_metrics(df, exclude=excluded))

    grouped = [((), df)] if not group_columns else list(df.groupby(group_columns, dropna=False))
    rows: list[dict] = []

    for key, group in grouped:
        if not isinstance(key, tuple):
            key = (key,)

        row = {column: value for column, value in zip(group_columns, key, strict=False)}
        row["n"] = int(len(group))

        if warn_small_n:
            row["warning_small_n"] = int(len(group) < 2)

        if success_column and success_column in group.columns:
            row["success_rate"] = float(coerce_success(group[success_column]).mean())

        for metric in selected_metrics:
            if metric not in group.columns:
                continue

            values = pd.to_numeric(group[metric], errors="coerce").dropna()
            row[f"{metric}_mean"] = float(values.mean()) if len(values) else float("nan")
            row[f"{metric}_std"] = float(values.std(ddof=1)) if len(values) > 1 else 0.0

            if compute_ci:
                lower, upper = bootstrap_mean_ci(values, iterations=ci_iterations)
                row[f"{metric}_ci95_lower"] = lower
                row[f"{metric}_ci95_upper"] = upper

        rows.append(row)

    summary = pd.DataFrame(rows)
    return summary.sort_values(group_columns).reset_index(drop=True) if group_columns else summary
