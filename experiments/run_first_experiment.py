"""Entry point for the first uncertainty-aware navigation experiment.

The initial experiment will compare classical shortest-path planning with an
uncertainty-weighted risk-aware planner on controlled grid-map environments.
"""
from __future__ import annotations

from pathlib import Path

import yaml


CONFIG_PATH = Path("configs/first_experiment.yaml")


def load_config(path: Path = CONFIG_PATH) -> dict:
    """Load the experiment configuration."""

    with path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def main() -> None:
    """Run the first experiment placeholder."""

    config = load_config()
    experiment_name = config["experiment"]["name"]
    print(f"Loaded experiment: {experiment_name}")
    print(
        "Implementation TODO: grid generation, baseline planning, "
        "risk-aware planning, and metric reporting."
    )


if __name__ == "__main__":
    main()
