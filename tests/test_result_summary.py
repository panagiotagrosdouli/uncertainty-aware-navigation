"""Tests for result summarization utilities."""
from __future__ import annotations

import pandas as pd

from uncertainty_navigation.result_summary import coerce_success, summarize_results


def test_coerce_success_handles_text_values() -> None:
    values = pd.Series(["success", "fail", "yes", "no"])
    result = coerce_success(values)

    assert result.tolist() == [True, False, True, False]


def test_summarize_results_groups_by_planner() -> None:
    df = pd.DataFrame(
        {
            "planner": ["astar", "astar", "risk"],
            "lambda_uncertainty": [0.0, 0.0, 1.0],
            "success": [True, False, True],
            "path_length": [10, 14, 12],
        }
    )

    summary = summarize_results(
        df=df,
        group_by=["planner", "lambda_uncertainty"],
        metrics=["path_length"],
    )

    astar_row = summary[summary["planner"] == "astar"].iloc[0]
    assert astar_row["n"] == 2
    assert astar_row["success_rate"] == 0.5
    assert astar_row["path_length_mean"] == 12.0
