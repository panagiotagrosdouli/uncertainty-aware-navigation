from __future__ import annotations

import argparse
import json

from uanav.robot_showcase import generate_showcase


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate closed-loop robot showcase logs.")
    parser.add_argument("--config", default="configs/showcase/robot_research_demo.yaml")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--output", default="results/demo/robot_showcase")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    print(json.dumps(generate_showcase(args.config, args.seed, args.output), indent=2))
