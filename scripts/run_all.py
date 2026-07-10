from __future__ import annotations

import argparse
import json

from uanav.belief_space import run_belief_space_demo
from uanav.demo import run_all as run_demo_all
from uanav.demo import run_synthetic_demo


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run uncertainty-aware navigation workflows.")
    parser.add_argument(
        "--mode",
        choices=("smoke", "demo", "belief-space", "full"),
        default="demo",
        help="Workflow to execute.",
    )
    return parser.parse_args()


def run_mode(mode: str) -> dict:
    if mode == "smoke":
        synthetic = run_synthetic_demo()
        belief_space = run_belief_space_demo()
        return {
            "mode": mode,
            "synthetic_success": synthetic["metrics"]["mission_completion"],
            "belief_space_success": belief_space.success,
        }
    if mode == "belief-space":
        return run_belief_space_demo().to_dict()
    if mode == "full":
        return {
            "mode": mode,
            "demo": run_demo_all(),
            "belief_space": run_belief_space_demo().to_dict(),
        }
    return {"mode": mode, "demo": run_demo_all()}


if __name__ == "__main__":
    print(json.dumps(run_mode(parse_args().mode), indent=2, default=str))
