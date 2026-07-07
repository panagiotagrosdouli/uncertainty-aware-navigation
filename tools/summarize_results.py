#!/usr/bin/env python3
"""Summarize experiment results from a CSV file."""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from uncertainty_navigation.result_summary import auto_numeric_metrics, summarize_results


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(description="Summarize uncertainty-aware navigation results.")
    parser.add_argument("--input", "-i", required=True, help="Input CSV path.")
    parser.add_argument(
        "--group-by",
        "-g",
        nargs="*",
        default=["planner", "lambda_uncertainty"],
        help="Columns used for grouping.",
    )
    parser.add_argument("--metrics", "-m", nargs="*", default=None, help="Metrics to summarize.")
    parser.add_argument("--success-column", default="success", help="Success column name.")
    parser.add_argument("--ci", action="store_true", help="Compute bootstrap confidence intervals.")
    parser.add_argument("--ci-iterations", type=int, default=2000, help="Bootstrap iterations.")
    parser.add_argument("--out", "-o", default=None, help="Optional output CSV path.")
    return parser.parse_args()


def main() -> int:
    """Run the summary CLI."""

    args = parse_args()
    input_path = Path(args.input)
    df = pd.read_csv(input_path)

    metrics = args.metrics or auto_numeric_metrics(
        df,
        exclude=[*args.group_by, args.success_column],
    )
    summary = summarize_results(
        df=df,
        group_by=args.group_by,
        metrics=metrics,
        success_column=args.success_column,
        compute_ci=args.ci,
        ci_iterations=args.ci_iterations,
    )

    with pd.option_context("display.max_columns", 200, "display.width", 160):
        print(summary)

    if args.out:
        output_path = Path(args.out)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        summary.to_csv(output_path, index=False)
        print(f"Wrote summary to: {output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
